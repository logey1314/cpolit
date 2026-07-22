import request from './request'

/**
 * 分页查询用户列表
 * @param {Object} params - { page, size, source }
 */
export function getUsers(params = {}) {
  return request({
    url: '/users',
    method: 'get',
    params: {
      page: params.page || 1,
      page_size: params.size || 10,
      source: params.source || undefined,
      keyword: params.keyword || undefined,
      segment_type: params.segment_type || undefined,
    },
  })
}

/**
 * 批量导入模拟用户
 * @param {Object} data - { source, users }
 */
export function importMockUsers(data) {
  return request({
    url: '/users/import',
    method: 'post',
    data: {
      source: data.source,
      users: data.users,
    },
  })
}

/**
 * 查询单个用户分层详情
 * @param {number} userId
 */
export function getUserSegment(userId) {
  return request({
    url: '/user-segments',
    method: 'get',
    params: { user_id: userId },
  })
}

/**
 * 查询用户身份归并记录
 * @param {number} userId
 */
export function getUserIdentities(userId) {
  return request({
    url: `/users/${userId}/identities`,
    method: 'get',
  })
}

/**
 * 标准化用户标签
 * @param {number} userId
 */
export function standardizeUserTags(userId) {
  return request({
    url: `/users/${userId}/tags`,
    method: 'put',
  })
}

/**
 * 人工调整分层
 * @param {number} userId
 * @param {Object} data - { segment_type, reason }
 */
export function adjustSegment(userId, data) {
  return request({
    url: `/user-segments/${userId}/adjust`,
    method: 'put',
    data: {
      segment_type: data.segment_type,
      reason: data.reason,
    },
  })
}

/**
 * AI 判断用户分层（触发分层计算）
 * @param {number} userId
 */
export function judgeSegment(userId) {
  return request({
    url: '/user-segments/judge',
    method: 'post',
    params: { user_id: userId },
  })
}
