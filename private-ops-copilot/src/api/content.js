import request from './request'

export function getContentDrafts(params = {}) {
  return request({
    url: '/content-drafts',
    method: 'get',
    params: {
      strategy_task_id: params.strategy_task_id || undefined,
      page: params.page || 1,
      page_size: params.page_size || 10,
    },
  })
}

export function generateMultiChannelContent(data) {
  return request({
    url: '/content-drafts/multi-channel',
    method: 'post',
    data: {
      strategy_task_id: data.strategy_task_id,
      channels: data.channels,
      base_draft_id: data.base_draft_id || null,
    },
  })
}

export function generateSingleContent(strategyTaskId, contentType) {
  return request({
    url: '/content-drafts/generate',
    method: 'post',
    data: {
      strategy_task_id: strategyTaskId,
      content_type: contentType || null,
    },
  })
}

export function updateContentDraft(draftId, contentText) {
  return request({
    url: `/content-drafts/${draftId}`,
    method: 'put',
    data: {
      content_text: contentText,
    },
  })
}

export function reviewContentDraft(draftId) {
  return request({
    url: '/compliance/review',
    method: 'post',
    data: {
      content_draft_id: draftId,
    },
  })
}
