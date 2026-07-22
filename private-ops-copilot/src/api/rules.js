import request from './request'

export function getComplianceLogs(params = {}) {
  return request({
    url: '/compliance/logs',
    method: 'get',
    params: {
      review_status: params.review_status || undefined,
      page: params.page || 1,
      page_size: params.page_size || 20,
    },
  })
}

export function confirmComplianceLog(logId, decision, reviewer) {
  return request({
    url: `/compliance/${logId}/confirm`,
    method: 'put',
    data: {
      decision,
      reviewer: reviewer || null,
    },
  })
}

export function getFrequencyRules(params = {}) {
  return request({
    url: '/frequency/rules',
    method: 'get',
    params: {
      dimension: params.dimension || undefined,
      channel: params.channel || undefined,
      page: params.page || 1,
      page_size: params.page_size || 50,
    },
  })
}

export function updateFrequencyRule(ruleId, data) {
  return request({
    url: `/frequency/rules/${ruleId}`,
    method: 'put',
    data: {
      max_count: data.max_count,
      window_hours: data.window_hours,
      is_active: data.is_active,
      rule_description: data.rule_description || null,
    },
  })
}
