cd /home/jupyter/MTCS_module && \
python universal_main_database.py \
  --task tasks/text_classification_for_custom_service/task_config.yaml \
  --iterations 100 \
  --db-path official_run_v4.db \
  --skip-auto-fixer \
  --wait-for-manual \
  --execution-timeout 7200 \
  --manual-timeout 86400
