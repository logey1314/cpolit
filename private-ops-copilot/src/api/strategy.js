import request from './request'

export function getStrategies(params = {}) {
  return request({
    url: '/touch-strategies',
    method: 'get',
    params: {
      user_id: params.user_id || undefined,
      confirm_status: params.confirm_status || undefined,
      keyword: params.keyword || undefined,
      segment_type: params.segment_type || undefined,
      touch_channel: params.touch_channel || undefined,
      page: params.page || 1,
      page_size: params.page_size || 10,
    },
  })
}

export function getStrategyCandidates(params = {}) {
  return request({
    url: '/touch-strategies/candidates',
    method: 'get',
    params: {
      keyword: params.keyword || undefined,
      source: params.source || undefined,
      confirm_status: params.confirm_status || undefined,
      segment_type: params.segment_type || undefined,
      touch_channel: params.touch_channel || undefined,
      page: params.page || 1,
      page_size: params.page_size || 10,
    },
  })
}

export function generateStrategy(userId, operationGoal) {
  return request({
    url: '/touch-strategies/generate',
    method: 'post',
    data: { user_id: userId, operation_goal: operationGoal },
  })
}

export function updateStrategyStatus(taskId, confirmStatus, assignee) {
  return request({
    url: `/touch-strategies/${taskId}/status`,
    method: 'put',
    data: { confirm_status: confirmStatus, assignee: assignee || null },
  })
}

export function getContentDrafts(strategyTaskId) {
  return request({
    url: '/content-drafts',
    method: 'get',
    params: { strategy_task_id: strategyTaskId, page: 1, page_size: 1 },
  })
}

export function generateContent(strategyTaskId, contentType) {
  return request({
    url: '/content-drafts/generate',
    method: 'post',
    data: { strategy_task_id: strategyTaskId, content_type: contentType || null },
  })
}

export function reviewContent(contentDraftId) {
  return request({
    url: '/compliance/review',
    method: 'post',
    data: { content_draft_id: contentDraftId },
  })
}

export function checkFrequency(userId, channel) {
  return request({
    url: '/frequency/check',
    method: 'post',
    data: { user_id: userId, channel: channel },
  })
}

export function confirmComplianceLog(logId, decision, reviewer) {
  return request({
    url: `/compliance/${logId}/confirm`,
    method: 'put',
    data: { decision: decision, reviewer: reviewer || null },
  })
}

export function createOperationTask(strategyTaskId, contentDraftId) {
  return request({
    url: '/operation-tasks/create',
    method: 'post',
    data: { strategy_task_id: strategyTaskId, content_draft_id: contentDraftId },
  })
}
