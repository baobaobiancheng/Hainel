// components/ReminderCard/ReminderCard.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    reminder: {
      type: Object,
      value: {},
    },
    showActions: {
      type: Boolean,
      value: true,
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
     * 点击提醒
     */
    onTap() {
      this.triggerEvent('tap', {
        reminder: this.data.reminder,
      })
    },

    /**
     * 标记完成
     */
    onComplete() {
      this.triggerEvent('complete', {
        reminder: this.data.reminder,
      })
    },

    /**
     * 编辑提醒
     */
    onEdit() {
      this.triggerEvent('edit', {
        reminder: this.data.reminder,
      })
    },

    /**
     * 删除提醒
     */
    onDelete() {
      this.triggerEvent('delete', {
        reminder: this.data.reminder,
      })
    },
  },
})

