import request from './request'

export function getOperationTasks(params = {}) {
  return request({
    url: '/operation-tasks',
    method: 'get',
    params: {
      assignee: params.assignee || undefined,
      status: params.status || undefined,
      page: params.page || 1,
      page_size: params.page_size || 10,
    },
  })
}

export function updateOperationTaskStatus(taskId, status, failReason) {
  return request({
    url: `/operation-tasks/${taskId}/status`,
    method: 'put',
    data: {
      status,
      fail_reason: failReason || null,
    },
  })
}
