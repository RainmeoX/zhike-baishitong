// 珠科百事通 - 全局配置
// 后端地址：PC 预览用 127.0.0.1；真机调试改成电脑局域网 IP（如 http://192.168.1.100:8000），
// 且后端需用 --host 0.0.0.0 启动
const API_BASE_URL = 'http://127.0.0.1:8000'

App({
  globalData: {
    apiBaseUrl: API_BASE_URL,
    userInfo: null
  },
  onLaunch() {
    // 启动时拉取本地缓存
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)
  }
})