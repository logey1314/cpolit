import request from './request'

export function getCommunities() {
  return request({
    url: '/communities',
    method: 'get',
  })
}

export function analyzeCommunity(data) {
  return request({
    url: '/interactions/analyze',
    method: 'post',
    data: {
      community_id: data.community_id || null,
      days: data.days ?? 7,
    },
  })
}

export function filterNoiseMessages(data = {}) {
  return request({
    url: '/community-interactions/filter-noise',
    method: 'post',
    params: {
      community_id: data.community_id || undefined,
      limit: data.limit || 100,
    },
  })
}

export function getCommunityMessages(params = {}) {
  return request({
    url: '/community-interactions',
    method: 'get',
    params: {
      community_id: params.community_id || undefined,
      days: params.days ?? 7,
      page: params.page || 1,
      page_size: params.page_size || 20,
    },
  })
}

export function getSilenceRisk(userId) {
  return request({
    url: `/interactions/silence/${userId}`,
    method: 'get',
  })
}
