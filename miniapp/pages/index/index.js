// pages/index/index.js - 首页搜索
Page({
  data: {
    inputValue: '',
    hotQuestions: [
      '报修电话是多少',
      '校园巴士线路怎么走',
      '什么时候开始选课',
      '四六级什么时候报名',
      '奖学金有哪些',
      '怎么转专业',
      '宿舍水费怎么交',
      '食堂就餐规定'
    ],
    history: []
  },

  onLoad() {
    const history = wx.getStorageSync('search_history') || []
    this.setData({ history })
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },

  onSearch() {
    const q = this.data.inputValue.trim()
    if (!q) return
    this._saveHistory(q)
    wx.navigateTo({ url: `/pages/result/result?q=${encodeURIComponent(q)}` })
  },

  onHotTap(e) {
    const q = e.currentTarget.dataset.q
    this._saveHistory(q)
    wx.navigateTo({ url: `/pages/result/result?q=${encodeURIComponent(q)}` })
  },

  onHistoryTap(e) {
    const q = e.currentTarget.dataset.q
    wx.navigateTo({ url: `/pages/result/result?q=${encodeURIComponent(q)}` })
  },

  clearHistory() {
    wx.removeStorageSync('search_history')
    this.setData({ history: [] })
  },

  _saveHistory(q) {
    const history = wx.getStorageSync('search_history') || []
    const idx = history.indexOf(q)
    if (idx > -1) history.splice(idx, 1)
    history.unshift(q)
    if (history.length > 10) history.pop()
    wx.setStorageSync('search_history', history)
    this.setData({ history })
  }
})