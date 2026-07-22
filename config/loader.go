package config

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// ReadConfig 從 YAML 文件加載配置
func ReadConfig(path string) (*AppConfig, error) {
	cfg := DefaultConfig()

	data, err := os.ReadFile(path)
	if err != nil {
		if !os.IsNotExist(err) {
			return nil, fmt.Errorf("failed to read config file: %w", err)
		}
		// 文件不存在，使用預設值並記錄
		fmt.Fprintf(os.Stderr, "warning: config file not found, using defaults\n")
		cfg.ApplyDefaults()
		return &cfg, nil
	}

	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	cfg.ApplyDefaults()

	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	return &cfg, nil
}
