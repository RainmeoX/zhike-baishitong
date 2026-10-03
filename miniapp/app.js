// 珠科百事通 - 全局配置
App({
  globalData: {
    apiBaseUrl: 'http://127.0.0.1:8000',
    userInfo: null
  },
  onLaunch() {
    // 启动时拉取本地缓存
    const logs = wx.getStorageSync('logs') || []
    logs.unshift(Date.now())
    wx.setStorageSync('logs', logs)
  }
})