package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/robfig/cron/v3"
)

const (
	// 替换成你的钉钉机器人 webhook 地址
	webhookURL = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
	// 替换成你的钉钉机器人密钥
	secret = "YOUR_SECRET"
)

func main() {
	fmt.Println("监控程序启动...")
	c := cron.New(cron.WithSeconds())

	// 修改为每分钟执行一次，方便测试
	_, err := c.AddFunc("0 0 * * * *", func() {
		fmt.Println("执行检查任务:", time.Now().Format("2006-01-02 15:04:05"))
		checkSystemLoad()
	})
	if err != nil {
		panic(err)
	}

	c.Start()
	fmt.Println("定时任务已启动")
	select {} // 保持程序运行
}

func checkSystemLoad() {
	load, err := getSystemLoad()
	if err != nil {
		fmt.Printf("获取系统负载失败: %v\n", err)
		return
	}

	fmt.Printf("当前系统负载: %.2f\n", load)

	// 如果1分钟负载大于2，发送告警
	if load > 2.0 {
		message := fmt.Sprintf("系统负载告警：当前负载为 %.2f", load)
		sendDingTalkAlert(message)
	}
}

func getSystemLoad() (float64, error) {
	content, err := ioutil.ReadFile("/proc/loadavg")
	if err != nil {
		return 0, err
	}

	var load float64
	_, err = fmt.Sscanf(string(content), "%f", &load)
	return load, err
}

func sendDingTalkAlert(message string) {
	timestamp := time.Now().UnixMilli()
	sign := generateSign(timestamp)

	webhookWithSign := fmt.Sprintf("%s&timestamp=%d&sign=%s", webhookURL, timestamp, sign)

	payload := fmt.Sprintf(`{
        "msgtype": "text",
        "text": {
            "content": "%s"
        }
    }`, message)

	resp, err := http.Post(webhookWithSign, "application/json", strings.NewReader(payload))
	if err != nil {
		fmt.Printf("发送钉钉消息失败: %v\n", err)
		return
	}
	defer resp.Body.Close()
}

func generateSign(timestamp int64) string {
	stringToSign := fmt.Sprintf("%d\n%s", timestamp, secret)
	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(stringToSign))

	return url.QueryEscape(base64.StdEncoding.EncodeToString(h.Sum(nil)))
}
