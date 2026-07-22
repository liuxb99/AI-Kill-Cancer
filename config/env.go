package config

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// LlamaEnv 存放從 .env 檔案讀取的 llama-server 配置
type LlamaEnv struct {
	ServerBin  string
	Model      string
	Host       string
	Port       string
	NGPU       string
	CtxLen     string
	Threads    string
	BatchSize  string
	UBatchSize string
	FlashAttn  string
	MLA        string
	MLock      string
	ExtraArgs  string
}

// DefaultLlamaEnv 返回預設的 llama-server 環境變數
func DefaultLlamaEnv() LlamaEnv {
	return LlamaEnv{
		ServerBin:  "llama-server",
		Model:      "",
		Host:       "127.0.0.1",
		Port:       "8080",
		NGPU:       "-1",
		CtxLen:     "4096",
		Threads:    "0",
		BatchSize:  "512",
		UBatchSize: "512",
		FlashAttn:  "auto",
		MLA:        "0",
		MLock:      "1",
		ExtraArgs:  "--no-cache",
	}
}

// LoadEnvFile 載入 .env 檔案，若檔案不存在則靜默使用環境變數或預設值
func LoadEnvFile(envPath string) (*LlamaEnv, error) {
	env := DefaultLlamaEnv()

	// 嘗試讀取 .env 檔案
	f, err := os.Open(envPath)
	if err != nil {
		if os.IsNotExist(err) {
			// 檔案不存在，使用環境變數 + 預設值
			env.applyEnvOverrides()
			return &env, nil
		}
		return nil, fmt.Errorf("failed to open %s: %w", envPath, err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		line := strings.TrimSpace(scanner.Text())
		// 跳過空行和註解
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		// 解析 key=value
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])
		if key == "" {
			continue
		}
		// 移除引號
		value = strings.Trim(value, `"'`)

		switch key {
		case "LLAMA_SERVER_BIN":
			env.ServerBin = value
		case "LLAMA_MODEL":
			env.Model = value
		case "LLAMA_HOST":
			env.Host = value
		case "LLAMA_PORT":
			env.Port = value
		case "LLAMA_N_GPU":
			env.NGPU = value
		case "LLAMA_CTX_LEN":
			env.CtxLen = value
		case "LLAMA_THREADS":
			env.Threads = value
		case "LLAMA_BATCH_SIZE":
			env.BatchSize = value
		case "LLAMA_UBATCH_SIZE":
			env.UBatchSize = value
		case "LLAMA_FLASH_ATTN":
			env.FlashAttn = value
		case "LLAMA_MLA":
			env.MLA = value
		case "LLAMA_MLOCK":
			env.MLock = value
		case "LLAMA_EXTRA_ARGS":
			env.ExtraArgs = value
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading %s: %w", envPath, err)
	}

	// 環境變數覆蓋（優先於 .env 檔案）
	env.applyEnvOverrides()

	return &env, nil
}

// applyEnvOverrides 檢查 LLAMA_* 環境變數，若存在則覆蓋設定
func (e *LlamaEnv) applyEnvOverrides() {
	if v := os.Getenv("LLAMA_SERVER_BIN"); v != "" {
		e.ServerBin = v
	}
	if v := os.Getenv("LLAMA_MODEL"); v != "" {
		e.Model = v
	}
	if v := os.Getenv("LLAMA_HOST"); v != "" {
		e.Host = v
	}
	if v := os.Getenv("LLAMA_PORT"); v != "" {
		e.Port = v
	}
	if v := os.Getenv("LLAMA_N_GPU"); v != "" {
		e.NGPU = v
	}
	if v := os.Getenv("LLAMA_CTX_LEN"); v != "" {
		e.CtxLen = v
	}
	if v := os.Getenv("LLAMA_THREADS"); v != "" {
		e.Threads = v
	}
	if v := os.Getenv("LLAMA_BATCH_SIZE"); v != "" {
		e.BatchSize = v
	}
	if v := os.Getenv("LLAMA_UBATCH_SIZE"); v != "" {
		e.UBatchSize = v
	}
	if v := os.Getenv("LLAMA_FLASH_ATTN"); v != "" {
		e.FlashAttn = v
	}
	if v := os.Getenv("LLAMA_MLA"); v != "" {
		e.MLA = v
	}
	if v := os.Getenv("LLAMA_MLOCK"); v != "" {
		e.MLock = v
	}
	if v := os.Getenv("LLAMA_EXTRA_ARGS"); v != "" {
		e.ExtraArgs = v
	}
}

// BuildArgs 將 LlamaEnv 轉換為 llama-server 的命令列參數
func (e *LlamaEnv) BuildArgs() []string {
	args := []string{}

	if e.Model != "" {
		args = append(args, "--model", e.Model)
	}

	args = append(args, "--host", e.Host)
	args = append(args, "--port", e.Port)

	if e.NGPU != "" && e.NGPU != "0" {
		args = append(args, "--n-gpu-layers", e.NGPU)
	}

	if e.CtxLen != "" && e.CtxLen != "0" {
		args = append(args, "--ctx-size", e.CtxLen)
	}

	if e.Threads != "" && e.Threads != "0" {
		args = append(args, "--threads", e.Threads)
	}

	if e.BatchSize != "" && e.BatchSize != "0" {
		args = append(args, "--batch-size", e.BatchSize)
	}

	if e.UBatchSize != "" && e.UBatchSize != "0" {
		args = append(args, "--ubatch-size", e.UBatchSize)
	}

	if e.FlashAttn != "" && e.FlashAttn != "0" {
		args = append(args, "--flash-attn", e.FlashAttn)
	}

	if e.MLA == "1" {
		args = append(args, "--mla")
	}

	if e.MLock == "1" {
		args = append(args, "--mlock")
	}

	// 附加額外參數（以空格分隔）
	if e.ExtraArgs != "" {
		extraParts := strings.Fields(e.ExtraArgs)
		args = append(args, extraParts...)
	}

	return args
}
