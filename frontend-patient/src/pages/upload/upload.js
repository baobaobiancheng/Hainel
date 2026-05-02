// pages/upload/upload.js

const REPORT_TYPES = [
  { icon: '❤️', label: '心电图', value: 'ecg' },
  { icon: '🩸', label: '血常规', value: 'blood' },
  { icon: '🔬', label: '生化检验', value: 'biochemistry' },
  { icon: '🫁', label: '影像报告', value: 'imaging' },
  { icon: '💊', label: '处方单', value: 'prescription' },
  { icon: '📋', label: '其他', value: 'other' },
]

let fileIdCounter = 0

Page({
  data: {
    files: [],
    selectedType: 'other',
    uploading: false,
    reportTypes: REPORT_TYPES,
    conversationId: null,
  },

  onLoad(options) {
    wx.setNavigationBarTitle({ title: '上传报告' })
    if (options.conversationId) {
      this.setData({ conversationId: parseInt(options.conversationId) })
    }
  },

  chooseAlbum() {
    wx.chooseImage({
      count: 9,
      sizeType: ['original', 'compressed'],
      sourceType: ['album'],
      success: (res) => this.addFiles(res.tempFiles, true),
    })
  },

  chooseFile() {
    wx.chooseMessageFile({
      count: 5,
      type: 'all',
      success: (res) => this.addFiles(res.tempFiles, false),
      fail: () => {
        // 降级到图片选择
        wx.chooseImage({
          count: 5,
          sizeType: ['original'],
          sourceType: ['album'],
          success: (res) => this.addFiles(res.tempFiles, true),
        })
      },
    })
  },

  // 允许的文件格式
  ALLOWED_EXTENSIONS: ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'pdf', 'doc', 'docx'],

  addFiles(tempFiles, isImage) {
    // 过滤不支持的文件格式
    const validFiles = []
    const invalidFiles = []

    tempFiles.forEach(f => {
      const name = f.name || `文件_${Date.now()}`
      const ext = name.split('.').pop().toLowerCase()

      if (!this.ALLOWED_EXTENSIONS.includes(ext)) {
        invalidFiles.push(name)
      } else {
        const size = f.size || 0
        validFiles.push({
          id: ++fileIdCounter,
          name,
          ext,
          tempPath: f.path || f.tempFilePath,
          sizeText: this.formatSize(size),
          isImage: isImage || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext),
          typeLabel: isImage ? '图片' : (ext === 'pdf' ? 'PDF文档' : '文件'),
          status: 'pending',
          progress: 0,
        })
      }
    })

    // 提示不支持的文件格式
    if (invalidFiles.length > 0) {
      wx.showToast({
        title: `不支持格式: ${invalidFiles.join(', ')}`,
        icon: 'none',
        duration: 3000,
      })
    }

    this.setData({ files: [...this.data.files, ...validFiles] })
  },

  formatSize(bytes) {
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`
  },

  deleteFile(e) {
    const idx = e.currentTarget.dataset.index
    const files = [...this.data.files]
    files.splice(idx, 1)
    this.setData({ files })
  },

  previewFile(e) {
    const idx = e.currentTarget.dataset.index
    const file = this.data.files[idx]
    if (file.isImage) {
      wx.previewImage({
        urls: [file.tempPath],
        current: file.tempPath,
      })
    }
  },

  selectType(e) {
    this.setData({ selectedType: e.currentTarget.dataset.value })
  },

  async submitReport() {
    if (this.data.files.length === 0) return
    if (!this.data.conversationId) {
      wx.showToast({ title: '会话无效', icon: 'none' })
      return
    }

    this.setData({ uploading: true })

    const app = getApp()
    const apiBase = app.globalData.apiBaseUrl
    const token = wx.getStorageSync('token')

    // 调试日志
    console.log('上传信息:', {
      apiBase,
      url: `${apiBase}/reports/upload`,
      conversationId: this.data.conversationId,
    })

    let successCount = 0
    const uploadedReports = []

    for (let i = 0; i < this.data.files.length; i++) {
      const file = this.data.files[i]
      this.updateFileStatus(i, 'uploading', 0)

      try {
        await new Promise((resolve, reject) => {
          wx.uploadFile({
            url: `${apiBase}/reports/upload`,
            filePath: file.tempPath,
            name: 'file',
            timeout: 120000, // 2分钟超时，大文件上传需要更长时间
            formData: {
              conversation_id: this.data.conversationId,
              report_type: this.data.selectedType,
              file_name: file.name,
            },
            header: { Authorization: `Bearer ${token}` },
            success: (res) => {
              if (res.statusCode >= 200 && res.statusCode < 300) {
                this.updateFileStatus(i, 'success', 100)
                successCount++
                try {
                  const data = JSON.parse(res.data || '{}')
                  uploadedReports.push({
                    messageId: data.id,
                    fileName: data.file_name || file.name,
                    metadata: data.metadata || {},
                  })
                } catch {
                  uploadedReports.push({ fileName: file.name, metadata: {} })
                }
                resolve(res)
              } else {
                this.updateFileStatus(i, 'error', 0)
                reject(new Error(`上传失败: ${res.statusCode}`))
              }
            },
            fail: (err) => {
              this.updateFileStatus(i, 'error', 0)
              reject(err)
            },
          })
        })
      } catch (err) {
        console.error(`文件 ${file.name} 上传失败:`, err)
      }
    }

    this.setData({ uploading: false })
    wx.showModal({
      title: '上传完成',
      content: successCount > 0
        ? `成功上传 ${successCount}/${this.data.files.length} 个文件，是否带入智能咨询分析？`
        : `成功上传 ${successCount}/${this.data.files.length} 个文件`,
      showCancel: successCount > 0,
      cancelText: '稍后分析',
      confirmText: successCount > 0 ? '立即分析' : '知道了',
      success: (modalRes) => {
        if (successCount > 0) {
          this.setData({ files: this.data.files.filter(f => f.status !== 'success') })
          if (modalRes.confirm) {
            wx.setStorageSync('pendingReportAnalysis', {
              conversationId: this.data.conversationId,
              reports: uploadedReports,
              prompt: '请结合我刚上传的报告进行分析，并说明报告中需要关注的异常项和下一步建议。',
            })
            wx.navigateBack()
          }
        }
      },
    })
  },

  updateFileStatus(index, status, progress) {
    const files = [...this.data.files]
    files[index] = { ...files[index], status, progress }
    this.setData({ files })
  },
})
