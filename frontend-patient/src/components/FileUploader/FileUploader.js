// components/FileUploader/FileUploader.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    maxCount: {
      type: Number,
      value: 9,
    },
    fileType: {
      type: String,
      value: 'all', // all, image, file
    },
    disabled: {
      type: Boolean,
      value: false,
    },
  },

  /**
   * 组件的初始数据
   */
  data: {
    files: [],
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 选择文件
     */
    chooseFile() {
      if (this.data.disabled) return

      if (this.data.fileType === 'image') {
        this.chooseImage()
      } else if (this.data.fileType === 'file') {
        this.chooseMessageFile()
      } else {
        // 显示选择器
        wx.showActionSheet({
          itemList: ['选择图片', '选择文件'],
          success: (res) => {
            if (res.tapIndex === 0) {
              this.chooseImage()
            } else {
              this.chooseMessageFile()
            }
          },
        })
      }
    },

    /**
     * 选择图片
     */
    chooseImage() {
      const maxCount = this.data.maxCount - this.data.files.length
      if (maxCount <= 0) {
        wx.showToast({
          title: `最多只能选择${this.data.maxCount}个文件`,
          icon: 'none',
        })
        return
      }

      wx.chooseImage({
        count: maxCount,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const files = res.tempFilePaths.map((path, index) => ({
            name: `图片${this.data.files.length + index + 1}.jpg`,
            path: path,
            size: 0,
            isImage: true,
            status: 'pending',
          }))
          this.addFiles(files)
        },
        fail: (err) => {
          console.error('选择图片失败:', err)
          this.triggerEvent('error', { err })
        },
      })
    },

    /**
     * 选择文件
     */
    chooseMessageFile() {
      const maxCount = this.data.maxCount - this.data.files.length
      if (maxCount <= 0) {
        wx.showToast({
          title: `最多只能选择${this.data.maxCount}个文件`,
          icon: 'none',
        })
        return
      }

      wx.chooseMessageFile({
        count: maxCount,
        type: 'file',
        success: (res) => {
          const files = res.tempFiles.map((file, index) => ({
            name: file.name,
            path: file.path,
            size: file.size,
            isImage: false,
            status: 'pending',
          }))
          this.addFiles(files)
        },
        fail: (err) => {
          console.error('选择文件失败:', err)
          this.triggerEvent('error', { err })
        },
      })
    },

    /**
     * 添加文件
     */
    addFiles(files) {
      const newFiles = [...this.data.files, ...files]
      this.setData({ files: newFiles })
      this.triggerEvent('change', { files: newFiles })
      
      // 自动上传
      this.uploadFiles(files)
    },

    /**
     * 上传文件
     */
    uploadFiles(files) {
      files.forEach(file => {
        this.uploadSingleFile(file)
      })
    },

    /**
     * 上传单个文件
     */
    uploadSingleFile(file) {
      // 更新状态为上传中
      this.updateFileStatus(file.path, {
        status: 'uploading',
        progress: 0,
      })

      // TODO: 实现实际上传逻辑
      // 触发上传事件，由父组件处理
      this.triggerEvent('upload', {
        file,
        callback: (result) => {
          if (result.success) {
            this.updateFileStatus(file.path, {
              status: 'success',
              progress: 100,
              fileId: result.fileId,
              url: result.url,
            })
          } else {
            this.updateFileStatus(file.path, {
              status: 'error',
            })
          }
        },
      })
    },

    /**
     * 更新文件状态
     */
    updateFileStatus(path, updates) {
      const files = this.data.files.map(file => {
        if (file.path === path) {
          return { ...file, ...updates }
        }
        return file
      })
      this.setData({ files })
      this.triggerEvent('change', { files })
    },

    /**
     * 删除文件
     */
    deleteFile(e) {
      const index = e.currentTarget.dataset.index
      const file = this.data.files[index]
      
      if (file.status === 'uploading') {
        wx.showToast({
          title: '文件上传中，无法删除',
          icon: 'none',
        })
        return
      }

      const files = [...this.data.files]
      files.splice(index, 1)
      this.setData({ files })
      this.triggerEvent('change', { files })
      this.triggerEvent('delete', { file, index })
    },

    /**
     * 预览文件
     */
    previewFile(e) {
      const index = e.currentTarget.dataset.index
      const file = this.data.files[index]
      
      if (file.isImage) {
        const urls = this.data.files
          .filter(f => f.isImage)
          .map(f => f.path)
        wx.previewImage({
          current: file.path,
          urls: urls,
        })
      } else {
        this.triggerEvent('preview', { file, index })
      }
    },
  },
})

