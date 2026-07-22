package config

import (
	"fmt"
	"net/url"
	"strings"
	"time"
)

// EngineType 推理引擎類型
type EngineType string

const (
	EngineTypeLlama   EngineType = "llama"
	EngineTypeUnsloth EngineType = "unsloth"
)

// IsValid 檢查枚舉值是否有效
func (e EngineType) IsValid() bool {
	return e == EngineTypeLlama || e == EngineTypeUnsloth
}

func (e EngineType) String() string {
	return string(e)
}

// ParseEngineType 解析字串為 EngineType，不合法回傳 EngineTypeLlama
func ParseEngineType(s string) EngineType {
	s = strings.ToLower(strings.TrimSpace(s))
	if s == "unsloth" {
		return EngineTypeUnsloth
	}
	return EngineTypeLlama
}

// AppConfig 應用程式配置
type AppConfig struct {
	EngineType    EngineType `yaml:"engine_type"`
	ServerURL     string     `yaml:"server_url"`
	WebUIPort     int        `yaml:"web_ui_port"`
	HealthInterval int       `yaml:"health_interval_sec"`
	RestartInterval int      `yaml:"restart_interval_sec"`
	HealthTimeout  int       `yaml:"health_timeout_sec"`
	MaxFailures    int       `yaml:"max_failures"`
	StatsEndpoint  string    `yaml:"stats_endpoint"`
	LogFile        string    `yaml:"log_file"`
	LogMaxSizeMB   int       `yaml:"log_max_size_mb"`
	LogMaxBackups  int       `yaml:"log_max_backups"`

	// 自動安裝配置
	AutoInstall       bool     `yaml:"auto_install"`
	RequiredPkgs      []string `yaml:"required_packages"`
	InstallScript     string   `yaml:"install_script"`
	InstallTimeoutSec int      `yaml:"install_timeout_sec"`

	// 模型管理配置
	ModelsDir string `yaml:"models_dir"` // 模型存放目錄

	// 穩定/復原配置
	MaxConsecutiveRestarts int     `yaml:"max_consecutive_restarts"`
	MaxBackoffSec          int     `yaml:"max_backoff_sec"`
	GPUMemLeakThreshold    float64 `yaml:"gpu_mem_leak_threshold"`
	TPSDegradationRatio    float64 `yaml:"tps_degradation_ratio"`
}

// DefaultConfig 返回預設配置
func DefaultConfig() AppConfig {
	return AppConfig{
		EngineType:     EngineTypeUnsloth,
		ServerURL:      "http://127.0.0.1:8080",
		WebUIPort:      9090,
		HealthInterval:  30,
		RestartInterval: 0,
		HealthTimeout:   10,
		MaxFailures:     3,
		StatsEndpoint:   "/v1/stats",
		LogFile:         "unsloth-manager.log",
		LogMaxSizeMB:    50,
		LogMaxBackups:   3,

		// 自動安裝
		AutoInstall:       true,
		RequiredPkgs:      []string{},
		InstallScript:     "",
		InstallTimeoutSec: 300,

		// 模型管理
		ModelsDir: "./models",

		// 穩定/復原
		MaxConsecutiveRestarts: 5,
		MaxBackoffSec:          60,
		GPUMemLeakThreshold:    20.0,
		TPSDegradationRatio:    0.5,
	}
}

// Validate 驗證配置欄位
func (c *AppConfig) Validate() error {
	if !c.EngineType.IsValid() {
		return fmt.Errorf("invalid engine_type: %q", c.EngineType)
	}
	if _, err := url.ParseRequestURI(c.ServerURL); err != nil {
		return fmt.Errorf("invalid server_url: %w", err)
	}
	if c.HealthInterval <= 0 {
		return fmt.Errorf("health_interval_sec must be positive")
	}
	if c.HealthTimeout <= 0 {
		return fmt.Errorf("health_timeout_sec must be positive")
	}
	if c.MaxFailures <= 0 {
		return fmt.Errorf("max_failures must be positive")
	}
	if c.LogMaxSizeMB <= 0 {
		return fmt.Errorf("log_max_size_mb must be positive")
	}
	if c.LogMaxBackups <= 0 {
		return fmt.Errorf("log_max_backups must be positive")
	}
	return nil
}

// ApplyDefaults 將零值替換為預設值
func (c *AppConfig) ApplyDefaults() {
	if c.EngineType == "" {
		c.EngineType = DefaultConfig().EngineType
	}
	if c.ServerURL == "" {
		c.ServerURL = DefaultConfig().ServerURL
	}
	if c.WebUIPort == 0 {
		c.WebUIPort = DefaultConfig().WebUIPort
	}
	if c.HealthInterval == 0 {
		c.HealthInterval = DefaultConfig().HealthInterval
	}
	if c.HealthTimeout == 0 {
		c.HealthTimeout = DefaultConfig().HealthTimeout
	}
	if c.MaxFailures == 0 {
		c.MaxFailures = DefaultConfig().MaxFailures
	}
	if c.StatsEndpoint == "" {
		c.StatsEndpoint = DefaultConfig().StatsEndpoint
	}
	if c.LogFile == "" {
		c.LogFile = DefaultConfig().LogFile
	}
	if c.LogMaxSizeMB == 0 {
		c.LogMaxSizeMB = DefaultConfig().LogMaxSizeMB
	}
	if c.LogMaxBackups == 0 {
		c.LogMaxBackups = DefaultConfig().LogMaxBackups
	}
	if c.RequiredPkgs == nil {
		def := DefaultConfig()
		c.RequiredPkgs = make([]string, len(def.RequiredPkgs))
		copy(c.RequiredPkgs, def.RequiredPkgs)
	}
	if c.InstallTimeoutSec == 0 {
		c.InstallTimeoutSec = DefaultConfig().InstallTimeoutSec
	}
	if c.MaxConsecutiveRestarts == 0 {
		c.MaxConsecutiveRestarts = DefaultConfig().MaxConsecutiveRestarts
	}
	if c.MaxBackoffSec == 0 {
		c.MaxBackoffSec = DefaultConfig().MaxBackoffSec
	}
	if c.GPUMemLeakThreshold == 0 {
		c.GPUMemLeakThreshold = DefaultConfig().GPUMemLeakThreshold
	}
	if c.TPSDegradationRatio == 0 {
		c.TPSDegradationRatio = DefaultConfig().TPSDegradationRatio
	}
	if c.ModelsDir == "" {
		c.ModelsDir = DefaultConfig().ModelsDir
	}
}

// Duration 輔助方法
func (c *AppConfig) HealthIntervalDuration() time.Duration {
	return time.Duration(c.HealthInterval) * time.Second
}

func (c *AppConfig) RestartIntervalDuration() time.Duration {
	return time.Duration(c.RestartInterval) * time.Second
}

func (c *AppConfig) HealthTimeoutDuration() time.Duration {
	return time.Duration(c.HealthTimeout) * time.Second
}
