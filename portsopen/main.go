package main

import (
	"bytes"
	"fmt"
	"net"
	"os"
	"time"

	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"

	"github.com/robfig/cron/v3"
)

var (
	previousPorts = make(map[int]bool)
)

func main() {
	c := cron.New()

	// 每小时执行一次
	c.AddFunc("@hourly", func() {
		currentPorts := getOpenPorts()
		savePortsToFile(currentPorts)

		if len(previousPorts) > 0 {
			diff := comparePorts(previousPorts, currentPorts)
			if len(diff) > 0 {
				sendAlert(diff)
			}
		}

		// 更新previousPorts
		previousPorts = currentPorts
	})

	c.Start()

	// 保持程序运行
	select {}
}

// 获取本机开放端口
func getOpenPorts() map[int]bool {
	ports := make(map[int]bool)

	// 检查1-65535端口
	for port := 1; port <= 65535; port++ {
		address := fmt.Sprintf(":%d", port)
		conn, err := net.DialTimeout("tcp", address, time.Second)
		if err == nil {
			ports[port] = true
			conn.Close()
		}
	}

	return ports
}

// 保存端口到文件
func savePortsToFile(ports map[int]bool) {
	f, err := os.Create("ports.txt")
	if err != nil {
		fmt.Println("无法创建文件:", err)
		return
	}
	defer f.Close()

	for port := range ports {
		fmt.Fprintln(f, port)
	}
}

// 比较两次端口差异
func comparePorts(old, new map[int]bool) map[int]string {
	diff := make(map[int]string)

	// 检查新增端口
	for port := range new {
		if !old[port] {
			diff[port] = "新增"
		}
	}

	// 检查关闭端口
	for port := range old {
		if !new[port] {
			diff[port] = "关闭"
		}
	}

	return diff
}

// 发送报警
func sendAlert(diff map[int]string) {
	// 只构建变化的端口信息
	msg := "端口变化报警：\n"
	for port, status := range diff {
		msg += fmt.Sprintf("端口 %d: %s\n", port, status)
	}

	// 调用钉钉报警
	err := sendDingTalkAlert(msg)
	if err != nil {
		fmt.Println("钉钉报警发送失败:", err)
	}
}

// 发送钉钉报警
func sendDingTalkAlert(msg string) error {
	// 钉钉webhook地址和签名密钥
	webhook := "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
	secret := "YOUR_SECRET"

	// 生成时间戳和签名
	timestamp := time.Now().UnixNano() / 1e6
	sign := generateDingTalkSign(secret, timestamp)

	// 构建请求URL
	requestURL := fmt.Sprintf("%s&timestamp=%d&sign=%s", webhook, timestamp, sign)

	// 构建请求体
	message := map[string]interface{}{
		"msgtype": "text",
		"text": map[string]string{
			"content": msg,
		},
	}

	// 将消息体转换为JSON
	jsonData, err := json.Marshal(message)
	if err != nil {
		return fmt.Errorf("JSON编码失败: %v", err)
	}

	// 发送请求
	resp, err := http.Post(requestURL, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("HTTP请求失败: %v", err)
	}
	defer resp.Body.Close()

	// 检查响应
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("钉钉API返回错误: 状态码 %d, 响应: %s", resp.StatusCode, string(body))
	}

	return nil
}

// 生成钉钉签名
func generateDingTalkSign(secret string, timestamp int64) string {
	stringToSign := fmt.Sprintf("%d\n%s", timestamp, secret)
	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(stringToSign))
	return base64.StdEncoding.EncodeToString(h.Sum(nil))
}
