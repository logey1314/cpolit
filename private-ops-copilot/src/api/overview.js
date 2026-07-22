import request from './request'

export function getSegmentDistribution() {
  return request({
    url: '/user-segments',
    method: 'get',
  })
}

export function getOperationTasks(params = {}) {
  return request({
    url: '/operation-tasks',
    method: 'get',
    params: {
      assignee: params.assignee || undefined,
      response_status: params.response_status || undefined,
      page: params.page || 1,
      page_size: params.page_size || 100,
    },
  })
}
