import shutil
import uuid
import time
import logging
import yaml
import random
from rich.logging import RichHandler
from rich.table import Table
from rich.console import Console
import rich.box
from typing import List, Optional, Union, cast
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from subprocess import Popen
from ea.launch import JobScheduler, JobConfig, ProcessWithLogging
from ea.database import ProgramDatabase, DatabaseConfig, Program
from ea.llm import (
    LLMClient,
    extract_between,
    EmbeddingClient,
    BanditBase,
    AsymmetricUCB,
)
from ea.edit import (
    apply_diff_patch,
    apply_full_patch,
    summarize_diff,
    redact_immutable,
)
from ea.core.sampler import PromptSampler
from ea.core.adaptive_patch import AdaptivePatchSelector
from ea.core.summarizer import MetaSummarizer
from ea.core.novelty_judge import NoveltyJudge
from ea.logo import print_gradient_logo

# Optional Kosmos integration
try:
    from ea.kosmos import KosmosAnalyzer, HybridKnowledgeManager, KosmosConfig
    KOSMOS_AVAILABLE = True
except ImportError:
    KOSMOS_AVAILABLE = False
    KosmosConfig = None

# Failure Memory integration for layered prompts
try:
    from ea.core.failure_memory import FailureMemory, build_layered_prompt_additions
    FAILURE_MEMORY_AVAILABLE = True
except ImportError:
    FAILURE_MEMORY_AVAILABLE = False
    FailureMemory = None

FOLDER_PREFIX = "gen"


@dataclass
class EvolutionConfig:
    task_sys_msg: Optional[str] = None
    patch_types: List[str] = field(default_factory=lambda: ["diff"])
    patch_type_probs: List[float] = field(default_factory=lambda: [1.0])
    num_generations: int = 10
    max_parallel_jobs: int = 2
    max_patch_resamples: int = 3
    max_patch_attempts: int = 5
    job_type: str = "local"
    language: str = "python"
    llm_models: List[str] = field(default_factory=lambda: ["azure-gpt-4.1-mini"])
    llm_dynamic_selection: Optional[Union[str, BanditBase]] = None
    llm_dynamic_selection_kwargs: dict = field(default_factory=lambda: {})
    llm_kwargs: dict = field(default_factory=lambda: {})
    meta_rec_interval: Optional[int] = None
    meta_llm_models: Optional[List[str]] = None
    meta_llm_kwargs: dict = field(default_factory=lambda: {})
    meta_max_recommendations: int = 5
    embedding_model: Optional[str] = None
    init_program_path: Optional[str] = "initial.py"
    results_dir: Optional[str] = None
    max_novelty_attempts: int = 3
    code_embed_sim_threshold: float = 1.0
    novelty_llm_models: Optional[List[str]] = None
    novelty_llm_kwargs: dict = field(default_factory=lambda: {})
    use_text_feedback: bool = False
    # Kosmos integration settings
    enable_kosmos: bool = False
    kosmos_config: Optional[dict] = None  # KosmosConfig as dict
    task_config: Optional[dict] = None  # Task configuration for Kosmos
    
    # Multi-initial program support (NEW)
    init_programs: Optional[List[str]] = None  # List of initial program paths
    init_program_assignment: str = "island"  # 'island', 'random', 'round_robin'
    
    # Plateau detection settings
    enable_plateau_detection: bool = True  # Set to False to let LLM rely on its own knowledge
    
    def get_init_programs(self) -> List[str]:
        """Get list of initial programs, falling back to single init_program_path."""
        if self.init_programs and len(self.init_programs) > 0:
            return self.init_programs
        elif self.init_program_path:
            return [self.init_program_path]
        return []


@dataclass
class RunningJob:
    """Represents a running job in the queue."""

    job_id: Union[str, Popen, ProcessWithLogging]
    exec_fname: str
    results_dir: str
    start_time: float
    generation: int
    parent_id: Optional[str]
    archive_insp_ids: List[str]
    top_k_insp_ids: List[str]
    code_diff: Optional[str]
    meta_patch_data: Optional[dict]
    code_embedding: List[float] = field(default_factory=list)
    embed_cost: float = 0.0
    novelty_cost: float = 0.0


# Set up logging
logger = logging.getLogger(__name__)


class EvolutionRunner:
    def __init__(
        self,
        evo_config: EvolutionConfig,
        job_config: JobConfig,
        db_config: DatabaseConfig,
        verbose: bool = True,
    ):
        self.evo_config = evo_config
        self.job_config = job_config
        self.db_config = db_config
        self.verbose = verbose

        print_gradient_logo((255, 0, 0), (255, 255, 255))
        if evo_config.results_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.results_dir = f"results_{timestamp}"
        else:
            self.results_dir = Path(evo_config.results_dir)

        if self.verbose:
            # Create log file path in results directory
            log_filename = f"{self.results_dir}/evolution_run.log"
            Path(self.results_dir).mkdir(parents=True, exist_ok=True)

            # Set up logging with both console and file handlers
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                handlers=[
                    RichHandler(
                        show_time=False, show_level=False, show_path=False
                    ),  # Console output (clean)
                    logging.FileHandler(
                        log_filename, mode="a", encoding="utf-8"
                    ),  # File output (detailed)
                ],
            )

            # Also log the initial setup information
            logger.info("=" * 80)
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Evolution run started at {start_time}")
            logger.info(f"Results directory: {self.results_dir}")
            logger.info(f"Log file: {log_filename}")
            logger.info("=" * 80)

        # Check if we are resuming a run
        resuming_run = False
        db_path = Path(f"{self.results_dir}/{db_config.db_path}")
        if self.evo_config.results_dir is not None and db_path.exists():
            resuming_run = True

        # Initialize LLM selection strategy
        if evo_config.llm_dynamic_selection is None:
            self.llm_selection = None
        elif isinstance(evo_config.llm_dynamic_selection, BanditBase):
            self.llm_selection = evo_config.llm_dynamic_selection
        elif (evo_config.llm_dynamic_selection.lower() == "ucb") or (
            evo_config.llm_dynamic_selection.lower() == "ucb1"
        ):
            self.llm_selection = AsymmetricUCB(
                arm_names=evo_config.llm_models,
                **evo_config.llm_dynamic_selection_kwargs,
            )
        else:
            raise ValueError("Invalid llm_dynamic_selection")

        # Initialize database and scheduler
        db_config.db_path = str(db_path)
        embedding_model_to_use = (
            evo_config.embedding_model or "text-embedding-3-small"
        )
        self.db = ProgramDatabase(
            config=db_config, embedding_model=embedding_model_to_use
        )
        self.scheduler = JobScheduler(
            job_type=evo_config.job_type,
            config=job_config,  # type: ignore
            verbose=verbose,
        )

        self.llm = LLMClient(
            model_names=evo_config.llm_models,
            model_selection=self.llm_selection,
            **evo_config.llm_kwargs,
            verbose=verbose,
        )
        if evo_config.embedding_model is not None:
            self.embedding = EmbeddingClient(
                model_name=evo_config.embedding_model,
                verbose=verbose,
            )
        else:
            self.embedding = None

        if evo_config.meta_llm_models is not None:
            self.meta_llm = LLMClient(
                model_names=evo_config.meta_llm_models,
                **evo_config.meta_llm_kwargs,
                verbose=verbose,
            )
        else:
            self.meta_llm = None

        if evo_config.novelty_llm_models is not None:
            self.novelty_llm = LLMClient(
                model_names=evo_config.novelty_llm_models,
                **evo_config.novelty_llm_kwargs,
                verbose=verbose,
            )
        else:
            self.novelty_llm = None

        # Initialize PromptSampler for handling LLM code prompts
        self.prompt_sampler = PromptSampler(
            task_sys_msg=evo_config.task_sys_msg,
            language=evo_config.language,
            patch_types=evo_config.patch_types,
            patch_type_probs=evo_config.patch_type_probs,
            use_text_feedback=evo_config.use_text_feedback,
        )
        
        # Initialize AdaptivePatchSelector for dynamic patch type adjustment
        self.adaptive_patch_selector = AdaptivePatchSelector(
            base_probs=evo_config.patch_type_probs,
            verbose=verbose,
        )

        # Initialize MetaSummarizer for meta-recommendations
        self.meta_summarizer = MetaSummarizer(
            meta_llm_client=self.meta_llm,
            language=evo_config.language,
            use_text_feedback=evo_config.use_text_feedback,
            max_recommendations=evo_config.meta_max_recommendations,
        )

        # Initialize NoveltyJudge for novelty assessment
        self.novelty_judge = NoveltyJudge(
            novelty_llm_client=self.novelty_llm,
            language=evo_config.language,
            similarity_threshold=evo_config.code_embed_sim_threshold,
            max_novelty_attempts=evo_config.max_novelty_attempts,
        )

        # Initialize rich console for formatted output
        self.console = Console()

        # Initialize Kosmos integration (if enabled)
        self.kosmos_analyzer = None
        self.kosmos_knowledge_mgr = None
        if evo_config.enable_kosmos and KOSMOS_AVAILABLE:
            logger.info("Initializing Kosmos integration...")
            try:
                # Create KosmosConfig from dict or use defaults
                if evo_config.kosmos_config:
                    kosmos_cfg = KosmosConfig.from_dict(evo_config.kosmos_config)
                else:
                    kosmos_cfg = KosmosConfig()
                
                # Get task config (use task_sys_msg as description if not provided)
                task_cfg = evo_config.task_config or {
                    'description': evo_config.task_sys_msg or 'ML optimization task',
                    'metric': 'combined_score',
                    'higher_is_better': True
                }
                
                # Initialize Kosmos components
                self.kosmos_analyzer = KosmosAnalyzer(
                    task_config=task_cfg,
                    kosmos_config=kosmos_cfg,
                    verbose=verbose
                )
                self.kosmos_knowledge_mgr = HybridKnowledgeManager.from_config(kosmos_cfg)
                
                logger.info("鉁?Kosmos integration initialized successfully")
            except Exception as e:
                logger.warning(f"鈿狅笍 Failed to initialize Kosmos: {e}")
                self.kosmos_analyzer = None
                self.kosmos_knowledge_mgr = None
        elif evo_config.enable_kosmos and not KOSMOS_AVAILABLE:
            logger.warning("鈿狅笍 Kosmos requested but not available (import failed)")

        # Initialize Failure Memory for layered prompts (Layer 3)
        self.failure_memory = None
        self.task_pitfalls_path = None
        if FAILURE_MEMORY_AVAILABLE:
            try:
                # Create failure memory database in results directory
                failure_db_path = Path(self.results_dir) / "failure_memory.json"
                self.failure_memory = FailureMemory(
                    db_path=str(failure_db_path),
                    verbose=verbose
                )
                
                # Look for task_pitfalls.yaml in the task directory
                if evo_config.init_program_path:
                    task_dir = Path(evo_config.init_program_path).parent
                    pitfalls_path = task_dir / "task_pitfalls.yaml"
                    if pitfalls_path.exists():
                        self.task_pitfalls_path = str(pitfalls_path)
                        logger.info(f"馃搵 Loaded task pitfalls from {pitfalls_path}")
                
                logger.info("鉁?Failure Memory initialized for layered prompts")
            except Exception as e:
                logger.warning(f"鈿狅笍 Failed to initialize Failure Memory: {e}")
                self.failure_memory = None

        if self.evo_config.language == "cuda":
            self.lang_ext = "cu"
        elif self.evo_config.language == "cpp":
            self.lang_ext = "cpp"
        elif self.evo_config.language == "python":
            self.lang_ext = "py"
        elif self.evo_config.language == "rust":
            self.lang_ext = "rs"
        else:
            msg = f"Language {self.evo_config.language} not supported"
            raise ValueError(msg)

        # Queue for managing parallel jobs
        self.running_jobs: List[RunningJob] = []
        self.best_program_id: Optional[str] = None
        self.next_generation_to_submit = 0

        if resuming_run:
            self.completed_generations = self.db.last_iteration + 1
            self.next_generation_to_submit = self.completed_generations
            logger.info("=" * 80)
            logger.info("RESUMING PREVIOUS EVOLUTION RUN")
            logger.info("=" * 80)
            logger.info(
                f"Resuming evolution from: {self.results_dir}\n"
                f"Found {self.completed_generations} "
                "previously completed generations."
            )
            logger.info("=" * 80)
            self._update_best_solution()
            # Restore meta memory state when resuming
            self._restore_meta_memory()
        else:
            self.completed_generations = 0

        # Save experiment configuration to a YAML file
        self._save_experiment_config(evo_config, job_config, db_config)

    def _save_experiment_config(
        self,
        evo_config: EvolutionConfig,
        job_config: JobConfig,
        db_config: DatabaseConfig,
    ) -> None:
        """Save experiment configuration to a YAML file."""
        config_data = {
            "evolution_config": asdict(evo_config),
            "job_config": asdict(job_config),
            "database_config": asdict(db_config),
            "timestamp": datetime.now().isoformat(),
            "results_directory": str(self.results_dir),
        }

        config_path = Path(self.results_dir) / "experiment_config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)

        logger.info(f"Experiment configuration saved to {config_path}")

    def run(self):
        """Run evolution with parallel job queue."""
        max_jobs = self.evo_config.max_parallel_jobs
        target_gens = self.evo_config.num_generations
        logger.info(
            f"Starting evolution with {max_jobs} parallel jobs, "
            f"target: {target_gens} generations"
        )

        # First, run generation 0 sequentially to populate the database
        if self.completed_generations == 0 and target_gens > 0:
            logger.info("Running generation 0 sequentially to initialize database...")
            self._run_generation_0()
            self.completed_generations = 1
            self.next_generation_to_submit = 1
            logger.info(f"Completed generation 0, total: 1/{target_gens}")

        # Now start parallel execution for remaining generations
        if self.completed_generations < target_gens:
            logger.info("Starting parallel execution for remaining generations...")

            # Main loop: monitor jobs and submit new ones
            while (
                self.completed_generations < target_gens or len(self.running_jobs) > 0
            ):
                # Check for completed jobs
                completed_jobs = self._check_completed_jobs()

                # Process completed jobs
                if completed_jobs:
                    for job in completed_jobs:
                        self._process_completed_job(job)

                    # Update completed generations count
                    self._update_completed_generations()

                    if self.verbose:
                        logger.info(
                            f"Processed {len(completed_jobs)} jobs. "
                            f"Total completed generations: "
                            f"{self.completed_generations}/{target_gens}"
                        )

                # Check if we've completed all generations
                if self.completed_generations >= target_gens:
                    logger.info("All generations completed, exiting...")
                    break

                # Submit new jobs to fill the queue (only if we have capacity)
                if (
                    len(self.running_jobs) < max_jobs
                    and self.next_generation_to_submit < target_gens
                ):
                    self._submit_new_job()

                # Wait a bit before checking again
                time.sleep(2)

            # All jobs are now handled by the main loop above

        # Perform final meta summary for any remaining unprocessed programs
        best_program = self.db.get_best_program()
        self.meta_summarizer.perform_final_summary(str(self.results_dir), best_program)

        # Save final meta memory state
        self._save_meta_memory()

        self.db.print_summary()
        logger.info(f"Evolution completed! {self.completed_generations} generations")
        logger.info("=" * 80)
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Evolution run ended at {end_time}")
        logger.info("=" * 80)

    def generate_initial_program(self):
        """Generate initial program with LLM, with retries."""
        llm_kwargs = self.llm.get_kwargs()

        sys_msg, user_msg = self.prompt_sampler.initial_program_prompt()
        # Store original prompts for tracking (before any retry modifications)
        original_sys_msg = sys_msg
        original_user_msg = user_msg
        msg_history = []
        total_costs = 0.0

        for attempt in range(self.evo_config.max_patch_attempts):
            response = self.llm.query(
                msg=user_msg,
                system_msg=sys_msg,
                llm_kwargs=llm_kwargs,
                msg_history=msg_history,
            )
            if response is None or response.content is None:
                if self.verbose:
                    logger.info(
                        f"  INITIAL PROGRAM ATTEMPT {attempt + 1}/"
                        f"{self.evo_config.max_patch_attempts} "
                        "FAILURE. Error: LLM response content was None."
                    )
                if attempt < self.evo_config.max_patch_attempts - 1:
                    user_msg = (
                        "The previous response was empty. Please try again "
                        "and provide the full code."
                    )
                    if response and response.new_msg_history:
                        msg_history = response.new_msg_history
                    continue
                else:
                    break

            total_costs += response.cost or 0
            initial_code = extract_between(
                response.content,
                f"```{self.evo_config.language}",
                "```",
                False,
            )

            if initial_code:
                patch_name = extract_between(
                    response.content, "<NAME>", "</NAME>", False
                )
                patch_description = extract_between(
                    response.content, "<DESCRIPTION>", "</DESCRIPTION>", False
                )
                if self.evo_config.language == "python":
                    comment_char = "#"
                else:
                    comment_char = "//"

                initial_code = (
                    f"{comment_char} EVOLVE-BLOCK-START\n"
                    f"{initial_code}\n"
                    f"{comment_char} EVOLVE-BLOCK-END\n"
                )

                if self.verbose:
                    logger.info(
                        f"  INITIAL PROGRAM ATTEMPT {attempt + 1}/"
                        f"{self.evo_config.max_patch_attempts} "
                        "SUCCESS."
                    )
                # Return prompts for tracking
                return initial_code, patch_name, patch_description, total_costs, original_sys_msg, original_user_msg
            else:  # code extraction failed
                if self.verbose:
                    logger.info(
                        f"  INITIAL PROGRAM ATTEMPT {attempt + 1}/"
                        f"{self.evo_config.max_patch_attempts} "
                        "FAILURE. Error: Could not extract code from response."
                    )
                if attempt < self.evo_config.max_patch_attempts - 1:
                    user_msg = (
                        "Could not extract code from your last response. "
                        "Please make sure to enclose the code in "
                        "`<CODE>`...`</CODE>` tags."
                    )
                    msg_history = response.new_msg_history
                else:  # last attempt
                    break

        raise ValueError(
            "LLM failed to generate a valid initial program after "
            f"{self.evo_config.max_patch_attempts} attempts."
        )

    def _run_generation_0(self):
        """Setup and run generation 0 to initialize the database.
        
        Supports multiple initial programs for diversity. If init_programs is 
        provided, each program is assigned to a different island. Otherwise,
        falls back to single init_program_path behavior.
        """
        init_programs = self.evo_config.get_init_programs()
        
        if len(init_programs) > 1:
            # Multi-initial program mode
            logger.info(f"馃尡 Multi-initial mode: {len(init_programs)} diverse programs")
            self._run_multi_initial_programs(init_programs)
        else:
            # Single initial program mode (legacy behavior)
            self._run_single_initial_program()
    
    def _run_single_initial_program(self):
        """Run generation 0 with a single initial program (legacy behavior)."""
        initial_dir = f"{self.results_dir}/{FOLDER_PREFIX}_0"
        Path(initial_dir).mkdir(parents=True, exist_ok=True)
        exec_fname = f"{initial_dir}/main.{self.lang_ext}"
        results_dir = f"{self.results_dir}/{FOLDER_PREFIX}_0/results"
        Path(results_dir).mkdir(parents=True, exist_ok=True)

        api_costs = 0.0
        patch_name = "initial_program"
        patch_description = "Initial program from file."
        patch_type = "init"
        # Default prompt values (will be overwritten if LLM is used)
        original_sys_msg = None
        original_user_msg = None

        if self.evo_config.init_program_path:
            if self.verbose:
                logger.info(
                    f"Copying initial program from {self.evo_config.init_program_path}"
                )
            shutil.copy(self.evo_config.init_program_path, exec_fname)
        else:
            if self.verbose:
                logger.info(
                    "`init_program_path` not provided, "
                    "generating initial program with LLM..."
                )
            initial_code, patch_name, patch_description, api_costs, original_sys_msg, original_user_msg = (
                self.generate_initial_program()
            )
            with open(exec_fname, "w", encoding="utf-8") as f:
                f.write(initial_code)

            if self.verbose:
                logger.info(f"Initial program generated and saved to {exec_fname}")

        # Run the evaluation synchronously
        results, rtime = self.scheduler.run(exec_fname, results_dir)

        code_embedding, e_cost = self.get_code_embedding(exec_fname)

        # Read the evaluated code for database insertion
        try:
            evaluated_code = Path(exec_fname).read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not read code for job {exec_fname}. Error: {e}")
            evaluated_code = ""

        correct_val = False
        metrics_val = {}
        stdout_log = ""
        stderr_log = ""
        if results:
            correct_val = results.get("correct", {}).get("correct", False)
            metrics_val = results.get("metrics", {})
            stdout_log = results.get("stdout_log", "")
            stderr_log = results.get("stderr_log", "")

        combined_score = metrics_val.get("combined_score", 0.0)
        public_metrics = metrics_val.get("public", {})
        private_metrics = metrics_val.get("private", {})
        text_feedback = metrics_val.get("text_feedback", "")

        # Add the program to the database
        db_program = Program(
            id=str(uuid.uuid4()),
            code=evaluated_code,
            language=self.evo_config.language,
            parent_id=None,
            generation=0,
            archive_inspiration_ids=[],
            top_k_inspiration_ids=[],
            code_diff=None,
            embedding=code_embedding,
            correct=correct_val,
            combined_score=combined_score,
            public_metrics=public_metrics,
            private_metrics=private_metrics,
            text_feedback=text_feedback,
            metadata={
                "compute_time": rtime,
                "api_costs": api_costs,
                "embed_cost": e_cost,
                "novelty_cost": 0.0,  # No novelty cost for generation 0
                "patch_type": patch_type,
                "patch_name": patch_name,
                "patch_description": patch_description,
                "stdout_log": stdout_log,
                "stderr_log": stderr_log,
                # Track actual prompts sent to LLM for debugging/analysis
                "llm_system_prompt": original_sys_msg,
                "llm_user_prompt": original_user_msg,
            },
        )

        self.db.add(db_program, verbose=True)
        if self.llm_selection is not None:
            self.llm_selection.set_baseline_score(
                db_program.combined_score if correct_val else 0.0,
            )
    
    def _run_multi_initial_programs(self, init_programs: List[str]):
        """
        Run generation 0 with multiple diverse initial programs.
        
        Each program is evaluated and assigned to a different island.
        This increases genetic diversity and helps avoid local optima.
        
        Args:
            init_programs: List of paths to initial program files
        """
        num_islands = self.db_config.num_islands
        assignment = self.evo_config.init_program_assignment
        
        logger.info(f"   Assignment strategy: {assignment}")
        logger.info(f"   Number of islands: {num_islands}")
        
        best_score = 0.0
        
        for idx, program_path in enumerate(init_programs):
            program_path = Path(program_path)
            
            if not program_path.exists():
                logger.warning(f"   鈿狅笍 Initial program not found: {program_path}")
                continue
            
            # Determine island assignment
            if assignment == "island":
                island_idx = idx % num_islands
            elif assignment == "random":
                island_idx = random.randint(0, num_islands - 1)
            else:  # round_robin
                island_idx = idx % num_islands
            
            logger.info(f"\n   馃搫 Program {idx + 1}/{len(init_programs)}: {program_path.name}")
            logger.info(f"      鈫?Assigned to Island {island_idx}")
            
            # Create directory for this initial program
            initial_dir = f"{self.results_dir}/{FOLDER_PREFIX}_0_{idx}"
            Path(initial_dir).mkdir(parents=True, exist_ok=True)
            exec_fname = f"{initial_dir}/main.{self.lang_ext}"
            results_dir = f"{initial_dir}/results"
            Path(results_dir).mkdir(parents=True, exist_ok=True)
            
            # Copy program
            shutil.copy(program_path, exec_fname)
            
            # Run evaluation
            results, rtime = self.scheduler.run(exec_fname, results_dir)
            
            # Get embedding
            code_embedding, e_cost = self.get_code_embedding(exec_fname)
            
            # Read code
            try:
                evaluated_code = Path(exec_fname).read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not read code: {e}")
                evaluated_code = ""
            
            # Parse results
            correct_val = False
            metrics_val = {}
            stdout_log = ""
            stderr_log = ""
            if results:
                correct_val = results.get("correct", {}).get("correct", False)
                metrics_val = results.get("metrics", {})
                stdout_log = results.get("stdout_log", "")
                stderr_log = results.get("stderr_log", "")
            
            combined_score = metrics_val.get("combined_score", 0.0)
            public_metrics = metrics_val.get("public", {})
            private_metrics = metrics_val.get("private", {})
            text_feedback = metrics_val.get("text_feedback", "")
            
            status = "鉁? if correct_val else "鉂?
            logger.info(f"      {status} Score: {combined_score:.4f}")
            
            # Create program record
            db_program = Program(
                id=str(uuid.uuid4()),
                code=evaluated_code,
                language=self.evo_config.language,
                parent_id=None,
                generation=0,
                island_idx=island_idx,  # Assign to specific island
                archive_inspiration_ids=[],
                top_k_inspiration_ids=[],
                code_diff=None,
                embedding=code_embedding,
                correct=correct_val,
                combined_score=combined_score,
                public_metrics=public_metrics,
                private_metrics=private_metrics,
                text_feedback=text_feedback,
                metadata={
                    "compute_time": rtime,
                    "api_costs": 0.0,
                    "embed_cost": e_cost,
                    "novelty_cost": 0.0,
                    "patch_type": "init",
                    "patch_name": f"initial_program_{idx}",
                    "patch_description": f"Initial program from {program_path.name}",
                    "stdout_log": stdout_log,
                    "stderr_log": stderr_log,
                    "init_program_path": str(program_path),
                    "init_program_idx": idx,
                    "llm_system_prompt": None,
                    "llm_user_prompt": None,
                },
            )
            
            self.db.add(db_program, verbose=True)
            
            # Track best score for baseline
            if correct_val and combined_score > best_score:
                best_score = combined_score
        
        # Set baseline score for LLM selection
        if self.llm_selection is not None:
            self.llm_selection.set_baseline_score(best_score)
        
        logger.info(f"\n   馃弳 Best initial score: {best_score:.4f}")
        self.db.save()
        self._update_best_solution()

        # Add the evaluated program to meta memory tracking
        self.meta_summarizer.add_evaluated_program(db_program)

        # Check if we should update meta memory after adding this program
        if self.meta_summarizer.should_update_meta(self.evo_config.meta_rec_interval):
            logger.info(
                f"Updating meta memory after processing "
                f"{len(self.meta_summarizer.evaluated_since_last_meta)} programs..."
            )
            best_program = self.db.get_best_program()
            updated_recs, meta_cost = self.meta_summarizer.update_meta_memory(
                best_program
            )
            if updated_recs:
                # Write meta output file for generation 0
                self.meta_summarizer.write_meta_output(str(self.results_dir))
                # Store meta cost for tracking
                if meta_cost > 0:
                    logger.info(
                        f"Meta recommendation generation cost: ${meta_cost:.4f}"
                    )
                    # Add meta cost to this program's metadata (the one that triggered the update)
                    if db_program.metadata is None:
                        db_program.metadata = {}
                    db_program.metadata["meta_cost"] = meta_cost
                    # Update the program in the database with the new metadata
                    import json

                    metadata_json = json.dumps(db_program.metadata)
                    self.db.cursor.execute(
                        "UPDATE programs SET metadata = ? WHERE id = ?",
                        (metadata_json, db_program.id),
                    )
                    self.db.conn.commit()

        # Save meta memory state after each job completion
        self._save_meta_memory()

    def _update_completed_generations(self):
        """
        Update the count of completed generations from the database.
        A generation `g` is considered complete if all generations from 0..g
        have at least one program in the database. This ensures the count
        advances sequentially without gaps.
        """
        last_gen = self.db.last_iteration
        if last_gen == -1:
            self.completed_generations = 0
            return

        # Check for contiguous generations from 0 up to last_gen
        completed_up_to = 0
        for i in range(last_gen + 1):
            if self.db.get_programs_by_generation(i):
                completed_up_to = i + 1
            else:
                # Found a gap, so contiguous sequence is broken
                self.completed_generations = completed_up_to
                return

        self.completed_generations = completed_up_to

    def _submit_new_job(self):
        """Submit a new job to the queue."""
        current_gen = self.next_generation_to_submit

        if current_gen >= self.evo_config.num_generations:
            return

        self.next_generation_to_submit += 1

        exec_fname = (
            f"{self.results_dir}/{FOLDER_PREFIX}_{current_gen}/main.{self.lang_ext}"
        )
        results_dir = f"{self.results_dir}/{FOLDER_PREFIX}_{current_gen}/results"
        Path(results_dir).mkdir(parents=True, exist_ok=True)

        # Get current meta-recommendations for this job
        meta_recs, meta_summary, meta_scratch = self.meta_summarizer.get_current()

        # Sample parent and inspiration programs
        if current_gen == 0:
            parent_id = None
            archive_insp_ids = []
            top_k_insp_ids = []
            code_diff = None
            meta_patch_data = {}
            # Initial program already copied in setup_initial_program
        else:
            api_costs = 0
            embed_cost = 0
            novelty_cost = 0.0
            novelty_checks_performed = 0
            # Loop over novelty attempts
            for nov_attempt in range(self.evo_config.max_novelty_attempts):
                # Loop over patch resamples - including parents
                for resample in range(self.evo_config.max_patch_resamples):
                    (
                        parent_program,
                        archive_programs,
                        top_k_programs,
                    ) = self.db.sample(
                        target_generation=current_gen,
                        novelty_attempt=nov_attempt + 1,
                        max_novelty_attempts=self.evo_config.max_novelty_attempts,
                        resample_attempt=resample + 1,
                        max_resample_attempts=self.evo_config.max_patch_resamples,
                    )
                    archive_insp_ids = [p.id for p in archive_programs]
                    top_k_insp_ids = [p.id for p in top_k_programs]
                    parent_id = parent_program.id
                    # Run patch (until success with max attempts)
                    code_diff, meta_patch_data, num_applied_attempt = self.run_patch(
                        parent_program,
                        archive_programs,
                        top_k_programs,
                        current_gen,
                        novelty_attempt=nov_attempt + 1,
                        resample_attempt=resample + 1,
                    )
                    api_costs += meta_patch_data["api_costs"]
                    if (
                        meta_patch_data["error_attempt"] is None
                        and num_applied_attempt > 0
                    ):
                        meta_patch_data["api_costs"] = api_costs
                        break

                # Get the code embedding for the evaluated code
                code_embedding, e_cost = self.get_code_embedding(exec_fname)
                embed_cost += e_cost

                if not code_embedding:
                    self.novelty_judge.log_novelty_skip_message("no embedding")
                    break

                # Use NoveltyJudge for novelty assessment with rejection sampling
                if self.novelty_judge.should_check_novelty(
                    code_embedding, current_gen, parent_program, self.db
                ):
                    should_accept, novelty_metadata = (
                        self.novelty_judge.assess_novelty_with_rejection_sampling(
                            exec_fname, code_embedding, parent_program, self.db
                        )
                    )

                    # Update costs and metadata from novelty assessment
                    novelty_cost += novelty_metadata.get("novelty_total_cost", 0.0)
                    novelty_checks_performed = novelty_metadata.get(
                        "novelty_checks_performed", 0
                    )
                    novelty_explanation = novelty_metadata.get(
                        "novelty_explanation", ""
                    )

                    if should_accept:
                        break
                    # If not accepted, continue to next attempt (rejection sampling)
                else:
                    if not self.db.island_manager or not hasattr(
                        self.db.island_manager, "are_all_islands_initialized"
                    ):
                        self.novelty_judge.log_novelty_skip_message("no island manager")
                    elif not self.db.island_manager.are_all_islands_initialized():
                        self.novelty_judge.log_novelty_skip_message(
                            "not all islands initialized yet"
                        )
                    break

        # Add meta-recommendations/summary/scratchpad to meta_patch_data
        if meta_recs is not None:
            meta_patch_data["meta_recommendations"] = meta_recs
            meta_patch_data["meta_summary"] = meta_summary
            meta_patch_data["meta_scratch_pad"] = meta_scratch

        # Add novelty check information to meta_patch_data if any checks were performed
        if current_gen > 0 and novelty_checks_performed > 0:
            meta_patch_data["novelty_checks_performed"] = novelty_checks_performed
            meta_patch_data["novelty_cost"] = novelty_cost
            meta_patch_data["novelty_explanation"] = novelty_explanation

        # Submit the job asynchronously
        job_id = self.scheduler.submit_async(exec_fname, results_dir)

        # Add to running jobs queue
        running_job = RunningJob(
            job_id=job_id,
            exec_fname=exec_fname,
            results_dir=results_dir,
            start_time=time.time(),
            generation=current_gen,
            parent_id=parent_id,
            archive_insp_ids=archive_insp_ids,
            top_k_insp_ids=top_k_insp_ids,
            code_diff=code_diff,
            meta_patch_data=meta_patch_data,
            code_embedding=code_embedding,
            embed_cost=embed_cost,
            novelty_cost=novelty_cost,
        )
        self.running_jobs.append(running_job)

        if self.verbose:
            logger.info(
                f"Submitted job for generation {current_gen}, "
                f"queue size: {len(self.running_jobs)}"
            )

    def _check_completed_jobs(self) -> List[RunningJob]:
        """Check for completed jobs and return them."""
        completed = []
        still_running = []

        for job in self.running_jobs:
            is_running = self.scheduler.check_job_status(job)
            if not is_running:
                # Job completed
                if self.verbose:
                    logger.info(f"Job {job.job_id} completed!")
                completed.append(job)
            else:
                # Job still running
                still_running.append(job)

        self.running_jobs = still_running
        return completed

    def _process_completed_job(self, job: RunningJob):
        """Process a completed job and add results to database."""
        end_time = time.time()
        rtime = end_time - job.start_time

        # Get job results
        results = self.scheduler.get_job_results(job.job_id, job.results_dir)

        # Read the evaluated code
        try:
            evaluated_code = Path(job.exec_fname).read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not read code for job {job.job_id}. Error: {e}")
            evaluated_code = ""

        # Use pre-computed embedding and novelty costs
        code_embedding = job.code_embedding
        e_cost = job.embed_cost
        n_cost = job.novelty_cost
        if self.verbose:
            logger.debug(
                f"=> Using pre-computed embedding for job {job.job_id}, "
                f"embed cost: {e_cost:.4f}, novelty cost: {n_cost:.4f}"
            )

        correct_val = False
        metrics_val = {}
        stdout_log = ""
        stderr_log = ""
        if results:
            correct_val = results.get("correct", {}).get("correct", False)
            metrics_val = results.get("metrics", {})
            stdout_log = results.get("stdout_log", "")
            stderr_log = results.get("stderr_log", "")

        combined_score = metrics_val.get("combined_score", 0.0)
        public_metrics = metrics_val.get("public", {})
        private_metrics = metrics_val.get("private", {})
        text_feedback = metrics_val.get("text_feedback", "")

        # Add the program to the database
        db_program = Program(
            id=str(uuid.uuid4()),
            code=evaluated_code,
            language=self.evo_config.language,
            parent_id=job.parent_id,
            generation=job.generation,
            archive_inspiration_ids=job.archive_insp_ids,
            top_k_inspiration_ids=job.top_k_insp_ids,
            code_diff=job.code_diff,
            embedding=code_embedding,
            correct=correct_val,
            combined_score=combined_score,
            public_metrics=public_metrics,
            private_metrics=private_metrics,
            text_feedback=text_feedback,
            metadata={
                "compute_time": rtime,
                **(job.meta_patch_data or {}),
                "embed_cost": e_cost,
                "novelty_cost": n_cost,
                "stdout_log": stdout_log,
                "stderr_log": stderr_log,
            },
        )
        self.db.add(db_program, verbose=True)

        # Record failure in Failure Memory (Layer 3) for future prompts
        if not correct_val and self.failure_memory:
            try:
                # Extract error message from public metrics or stderr
                error_msg = public_metrics.get('error', '')
                if not error_msg and stderr_log:
                    error_msg = stderr_log[:500]
                
                # Extract relevant code snippet (first 300 chars of main logic)
                code_snippet = evaluated_code[:300] if evaluated_code else ""
                
                self.failure_memory.record_failure(
                    gen_id=job.generation,
                    error_msg=error_msg,
                    code_snippet=code_snippet,
                    task_name=self.evo_config.task_sys_msg[:50] if self.evo_config.task_sys_msg else ""
                )
            except Exception as e:
                logger.warning(f"鈿狅笍 Failed to record failure in memory: {e}")

        # Kosmos analysis (if enabled and program is correct)
        if self.kosmos_analyzer and correct_val:
            try:
                logger.info(f"馃敩 Running Kosmos analysis for gen {job.generation}...")
                analysis_result = self.kosmos_analyzer.analyze_node(
                    code=evaluated_code,
                    metrics=metrics_val,
                    feature_importance=public_metrics.get('feature_importance', {})
                )
                
                if analysis_result.success:
                    # Store Kosmos insights in program metadata
                    if db_program.metadata is None:
                        db_program.metadata = {}
                    db_program.metadata['kosmos_insights'] = analysis_result.to_dict()
                    
                    # Update program in database
                    import json
                    metadata_json = json.dumps(db_program.metadata)
                    self.db.cursor.execute(
                        "UPDATE programs SET metadata = ? WHERE id = ?",
                        (metadata_json, db_program.id),
                    )
                    self.db.conn.commit()
                    
                    # Log top hypotheses
                    if analysis_result.hypotheses:
                        logger.info(f"馃搳 Kosmos found {len(analysis_result.hypotheses)} hypotheses:")
                        for h in analysis_result.hypotheses[:3]:
                            logger.info(f"   [{h.score:.2f}] {h.hypothesis[:60]}...")
                else:
                    logger.warning(f"鈿狅笍 Kosmos analysis failed: {analysis_result.error}")
            except Exception as e:
                logger.warning(f"鈿狅笍 Kosmos analysis error: {e}")

        # Add the evaluated program to meta memory tracking
        self.meta_summarizer.add_evaluated_program(db_program)

        # Check if we should update meta memory after adding this program
        if self.meta_summarizer.should_update_meta(self.evo_config.meta_rec_interval):
            logger.info(
                f"Updating meta memory after processing "
                f"{len(self.meta_summarizer.evaluated_since_last_meta)} programs..."
            )
            best_program = self.db.get_best_program()
            updated_recs, meta_cost = self.meta_summarizer.update_meta_memory(
                best_program
            )
            if updated_recs:
                # Write meta output file using accumulated program count
                self.meta_summarizer.write_meta_output(str(self.results_dir))
                # Store meta cost for tracking
                if meta_cost > 0:
                    logger.info(
                        f"Meta recommendation generation cost: ${meta_cost:.4f}"
                    )
                    # Add meta cost to this program's metadata (the one that triggered the update)
                    if db_program.metadata is None:
                        db_program.metadata = {}
                    db_program.metadata["meta_cost"] = meta_cost
                    # Update the program in the database with the new metadata
                    import json

                    metadata_json = json.dumps(db_program.metadata)
                    self.db.cursor.execute(
                        "UPDATE programs SET metadata = ? WHERE id = ?",
                        (metadata_json, db_program.id),
                    )
                    self.db.conn.commit()

        if self.llm_selection is not None:
            if "model_name" not in db_program.metadata:
                logger.warning(
                    "No model_name found in program metadata, "
                    "unable to update model selection algorithm."
                )
            else:
                parent = (
                    self.db.get(db_program.parent_id) if db_program.parent_id else None
                )
                baseline = parent.combined_score if parent else None
                reward = db_program.combined_score if correct_val else None
                model_name = db_program.metadata["model_name"]
                result = self.llm_selection.update(
                    arm=model_name,
                    reward=reward,
                    baseline=baseline,
                )
                if result and self.verbose:
                    normalized_score, baseline = result

                    def fmt(x):
                        return f"{x:.4f}" if isinstance(x, (float, int)) else "None"

                    logger.debug(
                        f"==> UPDATED LLM SELECTION: model: "
                        f"{model_name.split('/')[-1][-25:]}..., "
                        f"score: {fmt(normalized_score)}, "
                        f"raw score: {fmt(reward)}, baseline: {fmt(baseline)}"
                    )
                    self.llm_selection.print_summary()

        self.db.save()
        self._update_best_solution()
        
        # Update adaptive patch selector with current best score
        best_program = self.db.get_best_program()
        if best_program:
            self.adaptive_patch_selector.update(
                current_best_score=best_program.combined_score,
                generation=db_program.generation
            )
            # Update prompt sampler with new adaptive probabilities
            new_probs = self.adaptive_patch_selector.get_probs()
            self.prompt_sampler.patch_type_probs = new_probs

        # Note: Meta summarization check is now done after completed generations
        # are updated in the main loop to ensure correct timing

        # Save meta memory state after each job completion
        self._save_meta_memory()

    def _update_best_solution(self):
        """Checks and updates the best program."""
        best_programs = self.db.get_top_programs(n=1, correct_only=True)
        if not best_programs:
            if self.verbose:
                logger.debug(
                    "No correct programs found yet, cannot determine best solution."
                )
            return

        best_program = best_programs[0]

        if best_program.id == self.best_program_id:
            return  # No change

        self.best_program_id = best_program.id

        # For multi-initial programs in gen 0, find the specific subdirectory by checking scores
        source_dir = f"{self.results_dir}/{FOLDER_PREFIX}_{best_program.generation}"
        if not Path(source_dir).exists():
            # Check for multi-initial program directories (gen_0_0, gen_0_1, etc.)
            potential_dirs = list(Path(self.results_dir).glob(f"{FOLDER_PREFIX}_{best_program.generation}_*"))
            if potential_dirs:
                # Find the directory with the best score by reading metrics.json
                import json
                best_score = -float('inf')
                best_path = None
                for dir_path in potential_dirs:
                    metrics_file = dir_path / "results" / "metrics.json"
                    if metrics_file.exists():
                        try:
                            with open(metrics_file) as f:
                                metrics = json.load(f)
                                score = metrics.get('combined_score', 0)
                                if score > best_score:
                                    best_score = score
                                    best_path = dir_path
                        except:
                            pass
                
                if best_path:
                    source_dir = str(best_path)
                else:
                    logger.warning(f"Could not find source directory with valid metrics for gen {best_program.generation}")
                    return
            else:
                logger.warning(f"Source directory not found: {source_dir}")
                return
        
        best_dir = Path(self.results_dir) / "best"

        if best_dir.exists():
            shutil.rmtree(best_dir)

        shutil.copytree(source_dir, best_dir)

        if self.verbose:
            logger.info(
                f"New best program found: gen {best_program.generation}, "
                f"id {best_program.id[:6]}... "
                f"Copied to {best_dir}"
            )

    def _get_forced_exploration_guidance(self, generation: int, parent_program: Program) -> str:
        """
        Check if evolution is stuck and return forced exploration guidance.
        
        Triggers forced exploration when:
        - No improvement for N generations (plateau detected)
        - Uses ResearchDirector to select best research direction
        """
        # Check if plateau detection is disabled
        if not self.evo_config.enable_plateau_detection:
            logger.info("馃敩 Plateau detection disabled (LLM will rely on its own knowledge)")
            return ""
        
        try:
            # Import ResearchDirector
            from ea.knowledge.research_director import ResearchDirector, get_forced_exploration_guidance
            
            # Get recent performance history
            recent_programs = self.db.get_all_programs()[-50:]  # Last 50 generations
            if len(recent_programs) < 10:
                return ""  # Not enough history
            
            # Filter out suspicious scores (F1 >= 0.95 is likely data leakage)
            valid_programs = [p for p in recent_programs if p.combined_score is not None and p.combined_score < 0.95]
            logger.info(f"馃敩 ResearchDirector: {len(valid_programs)} valid programs (filtered {len(recent_programs) - len(valid_programs)} with score >= 0.95)")
            if not valid_programs:
                logger.warning("馃敩 ResearchDirector: No valid programs found, skipping forced exploration")
                return ""
            
            # Calculate plateau length
            best_score = max(p.combined_score for p in valid_programs)
            best_gen = max((p.generation for p in valid_programs if p.combined_score == best_score), default=0)
            plateau_length = generation - best_gen
            
            logger.info(f"馃敩 ResearchDirector: best_score={best_score:.4f} at gen {best_gen}, plateau_length={plateau_length}")
            
            # Only trigger if plateau is significant (> 10 generations)
            plateau_threshold = 10  # Increased to reduce forced exploration frequency
            if plateau_length < plateau_threshold:
                logger.info(f"馃敩 ResearchDirector: plateau_length {plateau_length} < threshold {plateau_threshold}, skipping")
                return ""
            
            logger.info(f"馃攳 Plateau detected: {plateau_length} generations without improvement (best={best_score:.4f} at gen {best_gen})")
            
            # Get failed approaches from recent generations
            failed_approaches = []
            for p in recent_programs[-20:]:
                if p.combined_score is not None and p.combined_score < best_score * 0.99:
                    if p.metadata and 'patch_name' in p.metadata:
                        failed_approaches.append(p.metadata['patch_name'])
            
            # Get current code summary
            current_code_summary = f"Current best: Gen {best_gen}, F1={best_score:.4f}"
            if parent_program.metadata and 'patch_description' in parent_program.metadata:
                current_code_summary += f"\nParent approach: {parent_program.metadata['patch_description']}"
            
            # Get performance history
            performance_history = [p.combined_score for p in recent_programs if p.combined_score is not None]
            
            # Use ResearchDirector to get guidance (with new research ideas pool + arXiv)
            # Create LLM client for intelligent selection
            try:
                from ea.llm.llm import LLMClient
                llm_client = LLMClient(
                    model_names=['gemini-3-pro-preview'],  # Use Gemini Pro 3 for research direction selection
                    max_tokens=32000,  # No restrictive limit for research direction selection
                    temperatures=0.7,
                )
            except Exception as e:
                logger.warning(f"Could not create LLM client for ResearchDirector: {e}")
                llm_client = None
            
            # Get task directory and look for task-specific research ideas
            task_ideas_path = None
            if self.evo_config.init_program_path:
                task_dir = Path(self.evo_config.init_program_path).parent
                potential_path = task_dir / "task_research_ideas.py"
                if potential_path.exists():
                    task_ideas_path = str(potential_path)
                    logger.info(f"馃摎 Found task-specific research ideas: {potential_path}")
            
            director = ResearchDirector(
                llm_client=llm_client, 
                use_new_pool=True,
                task_ideas_path=task_ideas_path  # NEW: Pass task-specific ideas path
            )
            
            # Get task-specific metric name from config
            metric_name = "Score"  # Default
            if self.evo_config.task_config and 'metric' in self.evo_config.task_config:
                metric_name = self.evo_config.task_config['metric'].upper()
            
            selection = director.select_direction_from_pool(
                best_score=best_score,  # Generic metric (F1, F-max, AUC, etc.)
                plateau_length=plateau_length,
                failed_approaches=failed_approaches,
                current_code_summary=current_code_summary,
                performance_history=performance_history,
                arxiv_papers="",  # Will be fetched automatically
                task_description=self.evo_config.task_sys_msg or "Optimization task",
                metric_name=metric_name,  # Task-specific metric name
            )
            
            guidance = director.get_forced_exploration_prompt(selection)
            
            # Log selected direction with more detail
            if 'idea' in selection and selection['idea'] is not None:
                idea = selection['idea']
                logger.info(f"馃毃 Selected research idea: [{idea.id}] {idea.name} (Expected: {idea.expected_f1_gain})")
            else:
                logger.info(f"馃毃 Selected research direction: {selection['direction'].name}")
            
            return guidance
            
        except ImportError:
            logger.warning("ResearchDirector not available, skipping forced exploration")
            return ""
        except Exception as e:
            logger.warning(f"Error in forced exploration: {e}")
            return ""

    def run_patch(
        self,
        parent_program: Program,
        archive_programs: List[Program],
        top_k_programs: List[Program],
        generation: int,
        novelty_attempt: int = 1,
        resample_attempt: int = 1,
    ) -> tuple[Optional[str], dict, int]:
        """Run patch generation for a specific generation."""
        max_patch_attempts = self.evo_config.max_patch_attempts
        if self.verbose:
            logger.info(
                f"Edit Cycle {generation} -> {generation + 1}, "
                f"Max Patch Attempts: {max_patch_attempts}"
            )
        # Get current meta recommendations
        meta_recs, _, _ = self.meta_summarizer.get_current()
        
        # Get Kosmos insights and knowledge (if enabled)
        kosmos_insights_str = ""
        kosmos_knowledge_str = ""
        if self.kosmos_analyzer and self.kosmos_knowledge_mgr:
            try:
                # Get parent's Kosmos insights if available
                if parent_program.metadata and 'kosmos_insights' in parent_program.metadata:
                    from ea.kosmos import AnalysisResult, RankedHypothesis
                    insights_dict = parent_program.metadata['kosmos_insights']
                    # Reconstruct AnalysisResult from dict
                    hypotheses = []
                    for h in insights_dict.get('hypotheses', []):
                        if isinstance(h, dict):
                            # Map 'type' to 'hypothesis_type' if present
                            h_copy = h.copy()
                            if 'type' in h_copy:
                                h_copy['hypothesis_type'] = h_copy.pop('type')
                            hypotheses.append(RankedHypothesis(**h_copy))
                        else:
                            hypotheses.append(h)
                    analysis_result = AnalysisResult(
                        hypotheses=hypotheses,
                        recommendations=insights_dict.get('recommendations', []),
                        success=True
                    )
                    kosmos_insights_str = self.kosmos_analyzer.format_for_mutation_prompt(analysis_result)
                
                # Get external knowledge (may trigger search on plateau)
                evolution_history = [
                    {'score': p.combined_score, 'model_type': p.metadata.get('patch_type', 'unknown') if p.metadata else 'unknown'}
                    for p in self.db.get_all_programs()[-50:]  # Last 50 programs
                ]
                knowledge_bundle = self.kosmos_knowledge_mgr.get_knowledge(
                    task_description=self.evo_config.task_sys_msg or '',
                    evolution_history=evolution_history,
                    current_gen=generation
                )
                kosmos_knowledge_str = self.kosmos_knowledge_mgr.format_for_mutation_prompt(knowledge_bundle)
                
                if knowledge_bundle.search_performed:
                    logger.info(f"馃攳 Kosmos external search triggered: {knowledge_bundle.search_reason}")
            except Exception as e:
                logger.warning(f"鈿狅笍 Error getting Kosmos insights: {e}")
        
        # Combine meta recommendations with Kosmos insights
        enhanced_meta_recs = meta_recs or ""
        if kosmos_insights_str:
            enhanced_meta_recs = f"{enhanced_meta_recs}\n{kosmos_insights_str}"
        if kosmos_knowledge_str:
            enhanced_meta_recs = f"{enhanced_meta_recs}\n{kosmos_knowledge_str}"
        
        # Add layered prompt additions (Layer 2: task pitfalls, Layer 3: failure memory)
        if FAILURE_MEMORY_AVAILABLE:
            layered_additions = build_layered_prompt_additions(
                failure_memory=self.failure_memory,
                task_pitfalls_path=self.task_pitfalls_path,
                max_warnings=5
            )
            if layered_additions:
                enhanced_meta_recs = f"{enhanced_meta_recs}\n{layered_additions}"
        
        # Check for plateau and add forced exploration if needed
        forced_exploration_str = self._get_forced_exploration_guidance(generation, parent_program)
        force_full_patch = False  # Track if we need to force full patch
        
        # Add forced exploration if plateau detected - PUT IT AT THE BEGINNING so LLM sees it first!
        if forced_exploration_str:
            # Put forced exploration at the BEGINNING, not the end
            enhanced_meta_recs = f"{forced_exploration_str}\n\n{'='*80}\n\n{enhanced_meta_recs}"
            force_full_patch = True  # Force full patch for exploration
            logger.info(f"馃毃 FORCED EXPLORATION triggered for Gen {generation} - Using FULL patch type")
            
            # IMPORTANT: Override patch type probabilities BEFORE sampling
            # This ensures the sampler uses "full" type and includes meta_recommendations
            original_probs = self.prompt_sampler.patch_type_probs.copy()
            self.prompt_sampler.patch_type_probs = [1.0 if t == "full" else 0.0 for t in self.prompt_sampler.patch_types]
            logger.info(f"馃攧 Forcing patch_type to 'full' for forced exploration (overriding sampler)")
        
        # Construct edit / code change message
        patch_sys, patch_msg, patch_type = self.prompt_sampler.sample(
            parent=parent_program,
            archive_inspirations=archive_programs,
            top_k_inspirations=top_k_programs,
            meta_recommendations=enhanced_meta_recs if enhanced_meta_recs.strip() else meta_recs,
        )
        
        # Restore original probabilities if we overrode them
        if force_full_patch:
            self.prompt_sampler.patch_type_probs = original_probs
        
        # Double-check patch_type is "full" when forced exploration is triggered
        if force_full_patch and patch_type != "full":
            logger.warning(f"鈿狅笍 Patch type was {patch_type} despite forcing - this shouldn't happen!")
            patch_type = "full"

        if patch_type in ["full", "cross"]:
            apply_patch = apply_full_patch
        elif patch_type == "diff":
            apply_patch = apply_diff_patch
        elif patch_type == "paper":
            raise NotImplementedError("Paper edit not implemented.")
            # apply_patch = apply_paper_patch
        else:
            raise ValueError(f"Invalid patch type: {patch_type}")

        total_costs = 0
        msg_history = []
        llm_kwargs = self.llm.get_kwargs()
        if self.llm_selection is not None:
            model_name = llm_kwargs["model_name"]
            self.llm_selection.update_submitted(model_name)
        code_diff = None  # Initialize code_diff
        num_applied_attempt = 0  # Initialize num_applied_attempt
        error_attempt = (
            "Max attempts reached without successful patch."  # Default error
        )
        patch_name = None
        patch_description = None
        output_path_attempt = None
        patch_txt_attempt = None
        patch_path = None
        diff_summary = {}

        for patch_attempt in range(max_patch_attempts):
            response = self.llm.query(
                msg=patch_msg,
                system_msg=patch_sys,
                msg_history=msg_history,
                llm_kwargs=llm_kwargs,
            )
            # print(response.content)
            if response is None or response.content is None:
                if self.verbose:
                    logger.info(
                        f"  PATCH ATTEMPT {patch_attempt + 1}/{max_patch_attempts} FAILURE. "
                        f"Error: LLM response content was None."
                    )
                # Prepare for next attempt or exit
                error_attempt = "LLM response content was None."
                num_applied_attempt = 0
                patch_txt_attempt = None
                if patch_attempt < max_patch_attempts - 1:
                    patch_msg = (
                        "The previous attempt to get an edit was not "
                        "successful because the LLM response was empty. "
                        "Try again."
                    )
                    if response:
                        msg_history = response.new_msg_history
                    continue
                else:  # Last attempt
                    break

            total_costs += response.cost  # Acc. cost
            patch_name = extract_between(
                response.content,
                "<NAME>",
                "</NAME>",
                False,
            )
            patch_description = extract_between(
                response.content,
                "<DESCRIPTION>",
                "</DESCRIPTION>",
                False,
            )

            # Apply the code patch (diff/full rewrite)
            (
                _,
                num_applied_attempt,
                output_path_attempt,
                error_attempt,
                patch_txt_attempt,
                patch_path,
            ) = apply_patch(
                original_str=parent_program.code,
                patch_str=response.content,
                patch_dir=f"{self.results_dir}/{FOLDER_PREFIX}_{generation}",
                language=self.evo_config.language,
                verbose=False,
            )

            if error_attempt is None and num_applied_attempt > 0:
                if patch_path:  # Ensure patch_path is not None
                    diff_summary = summarize_diff(
                        str(patch_path)
                    )  # Convert Path to str
                if self.verbose:
                    logger.info(
                        f"  PATCH ATTEMPT {patch_attempt + 1}/{max_patch_attempts} SUCCESS. "
                        f"Output: {output_path_attempt}, "
                        f"Patches Applied: {num_applied_attempt}."
                    )

                code_diff = patch_txt_attempt
                break  # Break from patch attempts
            else:
                error_str = (
                    str(error_attempt) if error_attempt else "No changes applied."
                )
                patch_msg = (
                    "The previous edit was not successful."
                    + " This was the error message: \n\n"
                    + error_str
                    + "\n\n Try again."
                )
                if self.verbose:
                    logger.info(
                        f"  PATCH ATTEMPT {patch_attempt + 1}/{max_patch_attempts} FAILURE. "
                        f"Error: '{error_str}', "
                        f"Patches Applied: {num_applied_attempt}."
                    )
                msg_history = response.new_msg_history
                code_diff = None
                if patch_attempt == max_patch_attempts - 1:  # Last attempt failed
                    # error_attempt is already set from apply_patch or default
                    pass

        # Only consider the diff summary for the original source file
        original_filename = f"original.{self.lang_ext}"
        if original_filename in diff_summary:
            diff_summary = diff_summary[original_filename]

        meta_edit_data = {
            "patch_type": patch_type,
            "api_costs": total_costs,
            "num_applied": num_applied_attempt,
            "patch_name": patch_name,
            "patch_description": patch_description,
            "error_attempt": error_attempt,
            "novelty_attempt": novelty_attempt,
            "resample_attempt": resample_attempt,
            "patch_attempt": patch_attempt + 1,
            **llm_kwargs,
            "llm_result": response.to_dict() if response else None,
            "diff_summary": diff_summary,
            # Track actual prompts sent to LLM for debugging/analysis
            "llm_system_prompt": patch_sys,
            "llm_user_prompt": patch_msg,
        }
        if self.verbose and num_applied_attempt > 0:
            self._print_metadata_table(meta_edit_data, generation)
        # Delete generation from meta_edit_data
        return code_diff, meta_edit_data, num_applied_attempt

    def get_code_embedding(self, exec_fname: str) -> tuple[List[float], float]:
        """Get the embedding of the code."""
        # Read the evaluated code
        try:
            evaluated_code = Path(exec_fname).read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not read code for job {exec_fname}. Error: {e}")
            evaluated_code = ""
        if evaluated_code != "":
            # Get the embedding of the initial program
            try:
                if self.embedding is not None:
                    redacted_code = redact_immutable(evaluated_code, no_state=True)
                    if self.verbose:
                        logger.debug(
                            "=> EMBED: Code length - "
                            f"Original: {len(evaluated_code)} - "
                            f"Redacted: {len(redacted_code)}"
                        )

                    embedding_result, e_cost = self.embedding.get_embedding(
                        redacted_code
                    )
                else:
                    if self.verbose:
                        logger.debug("=> EMBED: No embedding model configured.")
                    embedding_result = []
                    e_cost = 0.0
                code_embedding = cast(List[float], embedding_result)
            except Exception as e:
                logger.warning(f"Could not embed code for job {exec_fname}. Error: {e}")
                code_embedding = []
                e_cost = 0.0
        else:
            code_embedding = []
            e_cost = 0.0
        return code_embedding, e_cost

    def _print_metadata_table(self, meta_data: dict, generation: int):
        """Display metadata in a formatted rich table."""
        # Create title with generation and attempt information
        title_parts = ["[bold magenta]Patch Metadata"]

        # Add generation if present
        if generation is not None:
            title_parts.append(
                f" - Gen {generation}/{self.evo_config.num_generations} - Novelty: {meta_data['novelty_attempt']}/{self.evo_config.max_novelty_attempts} - Resample: {meta_data['resample_attempt']}/{self.evo_config.max_patch_resamples} - Patch: {meta_data['patch_attempt']}/{self.evo_config.max_patch_attempts}"
            )

        # Add attempt information if present
        if all(
            key in meta_data
            for key in [
                "novelty_attempt",
                "resample_attempt",
                "patch_attempt",
                "generation",
            ]
        ):
            title_parts.append(
                f" (Novelty: {meta_data['novelty_attempt']}, "
                f"Resample: {meta_data['resample_attempt']}, "
                f"Patch: {meta_data['patch_attempt']})"
            )

        title_parts.append("[/bold magenta]")
        table = Table(
            title="".join(title_parts),
            show_header=True,
            header_style="bold cyan",
            border_style="magenta",
            box=rich.box.ROUNDED,
            width=120,  # Match display.py table width
        )
        table.add_column("Field", style="cyan bold", no_wrap=True, width=25)
        table.add_column("Value", style="green", overflow="fold", width=90)

        # Define display order and formatting for specific fields
        display_order = [
            "patch_type",
            "patch_name",
            "patch_description",
            "num_applied",
            "api_costs",
            "error_attempt",
        ]

        # Add ordered fields first
        for field_name in display_order:
            if field_name in meta_data:
                value = meta_data[field_name]
                if value is None:
                    formatted_value = "[dim]None[/dim]"
                elif field_name == "api_costs":
                    formatted_value = f"${value:.4f}"
                elif field_name == "error_attempt" and value is None:
                    formatted_value = "[green]Success[/green]"
                elif field_name == "error_attempt":
                    formatted_value = (
                        f"[red]{str(value)[:100]}...[/red]"
                        if len(str(value)) > 100
                        else f"[red]{value}[/red]"
                    )
                else:
                    formatted_value = str(value)

                table.add_row(field_name, formatted_value)

        # Add remaining fields (excluding llm_result, diff_summary, and header info)
        skip_fields = set(
            display_order
            + [
                "llm_result",
                "diff_summary",
                "generation",
                "novelty_attempt",
                "resample_attempt",
                "patch_attempt",
            ]
        )
        for field_key, field_value in meta_data.items():
            if field_key not in skip_fields:
                if field_value is None:
                    formatted_value = "[dim]None[/dim]"
                else:
                    formatted_value = (
                        str(field_value)[:100] + "..."
                        if len(str(field_value)) > 100
                        else str(field_value)
                    )
                table.add_row(field_key, formatted_value)

        # Add diff summary if available
        if "diff_summary" in meta_data and meta_data["diff_summary"]:
            diff_summary = meta_data["diff_summary"]
            if isinstance(diff_summary, dict):
                summary_text = ""
                for k, v in diff_summary.items():
                    summary_text += f"{k}: {v}; "
                table.add_row("diff_summary", summary_text.strip())
            else:
                table.add_row("diff_summary", str(diff_summary)[:200])

        self.console.print(table)

    def _save_meta_memory(self) -> None:
        """Save the meta memory state to disk."""
        meta_memory_path = Path(self.results_dir) / "meta_memory.json"
        self.meta_summarizer.save_meta_state(str(meta_memory_path))

    def _restore_meta_memory(self) -> None:
        """Restore the meta memory state from disk."""
        meta_memory_path = Path(self.results_dir) / "meta_memory.json"

        if self.verbose:
            logger.info(f"Attempting to restore meta memory from: {meta_memory_path}")

        success = self.meta_summarizer.load_meta_state(str(meta_memory_path))
        if success:
            logger.info("Successfully restored meta memory state")
        else:
            if meta_memory_path.exists():
                logger.warning(
                    f"Meta memory file exists but failed to load: {meta_memory_path}"
                )
            else:
                logger.info("No previous meta memory state found - starting fresh")
