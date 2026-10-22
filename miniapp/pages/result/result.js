// pages/result/result.js - 搜索结果页
const app = getApp()

Page({
  data: {
    question: '',
    answer: '',
    confidence: 0,
    confidencePercent: 0,
    references: [],
    loading: true,
    error: ''
  },

  onLoad(options) {
    const q = decodeURIComponent(options.q || '')
    this.setData({ question: q })
    this._ask(q)
  },

  _ask(query) {
    this.setData({ loading: true, error: '' })
    wx.request({
      url: `${app.globalData.apiBaseUrl}/ask`,
      method: 'POST',
      data: { question: query, topk: 5 },
      header: { 'content-type': 'application/json' },
      timeout: 15000,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          this.setData({
            answer: res.data.answer || '',
            confidence: res.data.confidence || 0,
            confidencePercent: Math.round((res.data.confidence || 0) * 100),
            references: res.data.references || []
          })
        } else {
          this.setData({ error: '服务暂不可用，请稍后重试' })
        }
      },
      fail: () => {
        this.setData({ error: '网络连接失败，请检查网络后重试' })
      },
      complete: () => {
        this.setData({ loading: false })
      }
    })
  },

  onCopyUrl(e) {
    const url = e.currentTarget.dataset.url
    wx.setClipboardData({ data: url })
  },

  onNewSearch() {
    wx.navigateBack()
  }
})