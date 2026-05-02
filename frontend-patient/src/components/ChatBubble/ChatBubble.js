// components/ChatBubble/ChatBubble.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    message: {
      type: Object,
      value: {},
    },
    isUser: {
      type: Boolean,
      value: false,
    },
  },

  /**
   * 组件的初始数据
   */
  data: {

  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 点击消息
     */
    onTap() {
      this.triggerEvent('tap', {
        message: this.data.message,
      })
    },

    /**
     * 长按消息
     */
    onLongPress() {
      this.triggerEvent('longpress', {
        message: this.data.message,
      })
    },
  },
})

