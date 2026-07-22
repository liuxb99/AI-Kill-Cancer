package config

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// UnslothEnv 存放從 unsloth/.env 檔案讀取的 Unsloth 引擎配置
type UnslothEnv struct {
	PythonPath     string // UNSLOTH_PYTHON: Python 執行檔路徑
	VenvPath       string // UNSLOTH_VENV: 虛擬環境路徑
	ModelPath      string // UNSLOTH_MODEL: 模型檔案路徑
	Host           string // UNSLOTH_HOST: API 綁定地址
	Port           string // UNSLOTH_PORT: API 埠號
	GPULayers      int    // UNSLOTH_GPU_LAYERS: GPU 層數 (-1=自動)
	CtxLen         int    // UNSLOTH_CTX_LEN: 上下文窗口大小
	BatchSize      int    // UNSLOTH_BATCH_SIZE: 批次大小
	MaxBatchSize   int    // UNSLOTH_MAX_BATCH_SIZE: 最大批次大小
	Threads        int    // UNSLOTH_THREADS: 執行緒數
	FP16           bool   // UNSLOTH_FP16: 是否使用 FP16
	LoadFormat     string // UNSLOTH_LOAD_FORMAT: 加載格式
	ExtraArgs      string // UNSLOTH_EXTRA_ARGS: 額外參數
}

// DefaultUnslothEnv 返回預設的 Unsloth 環境變數
func DefaultUnslothEnv() UnslothEnv {
	return UnslothEnv{
		PythonPath:   "",
		VenvPath:     "unsloth/studio/backend/.venv",
		ModelPath:    "",
		Host:         "127.0.0.1",
		Port:         "8080",
		GPULayers:    -1,
		CtxLen:       4096,
		BatchSize:    512,
		MaxBatchSize: 512,
		Threads:      0,
		FP16:         true,
		LoadFormat:   "auto",
		ExtraArgs:    "",
	}
}

// LoadUnslothEnv 載入 unsloth/.env 檔案
func LoadUnslothEnv(envPath string) (*UnslothEnv, error) {
	env := DefaultUnslothEnv()

	f, err := os.Open(envPath)
	if err != nil {
		if os.IsNotExist(err) {
			env.applyEnvOverrides()
			return &env, nil
		}
		return nil, fmt.Errorf("failed to open %s: %w", envPath, err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(strings.Trim(parts[1], `"'`))
		if key == "" {
			continue
		}
		switch key {
		case "UNSLOTH_PYTHON":
			env.PythonPath = value
		case "UNSLOTH_VENV":
			env.VenvPath = value
		case "UNSLOTH_MODEL":
			env.ModelPath = value
		case "UNSLOTH_HOST":
			env.Host = value
		case "UNSLOTH_PORT":
			env.Port = value
		case "UNSLOTH_GPU_LAYERS":
			v, err := strconv.Atoi(value)
			if err == nil {
				env.GPULayers = v
			}
		case "UNSLOTH_CTX_LEN":
			v, err := strconv.Atoi(value)
			if err == nil && v > 0 {
				env.CtxLen = v
			}
		case "UNSLOTH_BATCH_SIZE":
			v, err := strconv.Atoi(value)
			if err == nil && v > 0 {
				env.BatchSize = v
			}
		case "UNSLOTH_MAX_BATCH_SIZE":
			v, err := strconv.Atoi(value)
			if err == nil && v > 0 {
				env.MaxBatchSize = v
			}
		case "UNSLOTH_THREADS":
			v, err := strconv.Atoi(value)
			if err == nil && v >= 0 {
				env.Threads = v
			}
		case "UNSLOTH_FP16":
			env.FP16 = value == "1" || value == "true" || value == "True"
		case "UNSLOTH_LOAD_FORMAT":
			env.LoadFormat = value
		case "UNSLOTH_EXTRA_ARGS":
			env.ExtraArgs = value
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading %s: %w", envPath, err)
	}

	env.applyEnvOverrides()
	return &env, nil
}

// applyEnvOverrides 檢查 UNSLOTH_* 環境變數覆蓋
func (e *UnslothEnv) applyEnvOverrides() {
	if v := os.Getenv("UNSLOTH_PYTHON"); v != "" {
		e.PythonPath = v
	}
	if v := os.Getenv("UNSLOTH_VENV"); v != "" {
		e.VenvPath = v
	}
	if v := os.Getenv("UNSLOTH_MODEL"); v != "" {
		e.ModelPath = v
	}
	if v := os.Getenv("UNSLOTH_HOST"); v != "" {
		e.Host = v
	}
	if v := os.Getenv("UNSLOTH_PORT"); v != "" {
		e.Port = v
	}
	if v := os.Getenv("UNSLOTH_GPU_LAYERS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			e.GPULayers = n
		}
	}
	if v := os.Getenv("UNSLOTH_CTX_LEN"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			e.CtxLen = n
		}
	}
	if v := os.Getenv("UNSLOTH_BATCH_SIZE"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			e.BatchSize = n
		}
	}
	if v := os.Getenv("UNSLOTH_MAX_BATCH_SIZE"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			e.MaxBatchSize = n
		}
	}
	if v := os.Getenv("UNSLOTH_THREADS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n >= 0 {
			e.Threads = n
		}
	}
	if v := os.Getenv("UNSLOTH_FP16"); v != "" {
		e.FP16 = v == "1" || v == "true" || v == "True"
	}
	if v := os.Getenv("UNSLOTH_LOAD_FORMAT"); v != "" {
		e.LoadFormat = v
	}
	if v := os.Getenv("UNSLOTH_EXTRA_ARGS"); v != "" {
		e.ExtraArgs = v
	}
}

// BuildCommand 將 UnslothEnv 轉換為啟動命令與參數
// run.py 支援的參數：--host, --port, --frontend, --silent, --api-only,
// --cloudflare/--no-cloudflare, --parallel
// ctx-len, batch-size, fp16 等由 run.py 內部自動偵測或透過環境變數設定
func (e *UnslothEnv) BuildCommand() (string, []string) {
	var cmd string
	var args []string

	// 優先使用指定的 Python 路徑
	if e.PythonPath != "" {
		cmd = e.PythonPath
	} else if e.VenvPath != "" {
		cmd = e.resolvePythonPath()
	} else {
		cmd = "python"
	}

	// 主要啟動指令（透過 launch_unsloth.py 包裝，載入相容性修補）
	args = append(args, "launch_unsloth.py")

	// 主機與埠號（run.py 預設埠為 8888，我們用 8080）
	args = append(args, "--host", e.Host)
	args = append(args, "--port", e.Port)

	return cmd, args
}

// resolvePythonPath 根據虛擬環境路徑解析 Python 執行檔
func (e *UnslothEnv) resolvePythonPath() string {
	if e.VenvPath == "" {
		return "python"
	}
	// Windows 優先
	candidates := []string{
		filepath.Join(e.VenvPath, "Scripts", "python.exe"),
		filepath.Join(e.VenvPath, "bin", "python3"),
		filepath.Join(e.VenvPath, "bin", "python"),
		filepath.Join(e.VenvPath, "python.exe"),
	}
	for _, p := range candidates {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return "python"
}
