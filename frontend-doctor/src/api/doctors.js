import request from './request'

export const getDashboardOverview = (range = '7d') => {
  return request({
    url: '/v1/doctors/dashboard-overview',
    method: 'get',
    params: { range }
  })
}
