#!/usr/bin/env python3
import sys
import os
import json

def load_config(path):
    default_config = {
        "patch_character_selection": True,
        "patch_in_game_models": True
    }
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(default_config, f, indent=2)
        return default_config
    
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except Exception:
            return default_config

def save_config(path, config):
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)

def main():
    config_path = 'workspace/patch_config.json'
    config = load_config(config_path)
    
    if len(sys.argv) < 2:
        print("Usage: python toggle_config.py [charsel | gameplay | status]")
        sys.exit(1)
        
    action = sys.argv[1].lower()
    
    if action == "charsel":
        config["patch_character_selection"] = not config.get("patch_character_selection", True)
        save_config(config_path, config)
    elif action == "gameplay":
        config["patch_in_game_models"] = not config.get("patch_in_game_models", True)
        save_config(config_path, config)
        
    # Print clean configuration status for batch shell integration
    cs = "ENABLED" if config.get("patch_character_selection", True) else "DISABLED"
    gp = "ENABLED" if config.get("patch_in_game_models", True) else "DISABLED"
    
    print(f"CHARSEL={cs}")
    print(f"GAMEPLAY={gp}")

if __name__ == '__main__':
    main()
