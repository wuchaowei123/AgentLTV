# Manual Execution Guide

## When AI System Times Out

1. **Extract failing node code:**
```bash
python manual_execution_helper.py core/sandbox/exe_code/node_XXXX.py
```

2. **Run the generated manual script:**
```bash
python core/sandbox/exe_code/node_XXXX_manual.py
```

3. **If it fails, edit and fix:**
```bash
nano core/sandbox/exe_code/node_XXXX_manual.py
# Fix imports, data paths, logic errors
python core/sandbox/exe_code/node_XXXX_manual.py
```

4. **Submit results to system:**
```bash
# For success:
python manual_update_result.py --node-id XXXX --score 0.85 --success --db-path YOUR_DB.db

# For failure:
python manual_update_result.py --node-id XXXX --error "Error message" --db-path YOUR_DB.db
```

## Common Issues & Fixes

### Data Loading Issues
- Fix paths in the manual script
- Ensure data files exist
- Check column names match

### Import Errors
- Add missing imports
- Install missing packages: `pip install package_name`

### Variable Name Issues
- Ensure code creates `val_predictions` variable
- Check for typos in variable names

## Example Workflow

For node_93662b2c that timed out:

```bash
# 1. Create manual script
python manual_execution_helper.py core/sandbox/exe_code/node_93662b2c.py

# 2. Run manual script
python core/sandbox/exe_code/node_93662b2c_manual.py

# 3. If successful, submit to system
python manual_update_result.py \
  --node-id 93662b2c \
  --score 0.4890 \
  --success \
  --db-path final_test.db

# 4. Resume AI system
python universal_main_database.py \
  --task tasks/kaggle_machine_failures/task_config.yaml \
  --iterations 5 \
  --enable-all-phases \
  --research-enhanced \
  --multi-strategy-init \
  --db-path final_test.db \
  --verbose
```

## Debugging Tips

### Check Core Code Only
```bash
python manual_execution_helper.py core/sandbox/exe_code/node_93662b2c.py --extract-only
```

### Custom Output File
```bash
python manual_execution_helper.py core/sandbox/exe_code/node_93662b2c.py --output debug_script.py
```

### Check Database Status
```bash
python execution_monitor.py --db-path final_test.db --status
python execution_monitor.py --db-path final_test.db --manual
```

## Resume System After Manual Fix
```bash
python universal_main_database.py --task TASK_CONFIG --db-path YOUR_DB.db --iterations N
```

The system will automatically continue from where it left off!
