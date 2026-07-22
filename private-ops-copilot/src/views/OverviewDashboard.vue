<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getContentDrafts } from '../api/content'
import { getOperationTasks, getSegmentDistribution } from '../api/overview'

const router = useRouter()
const loading = ref(false)
const segmentItems = ref([])
const operationTasks = ref([])
const contentDrafts = ref([])
const chartRef = ref(null)
let chartInstance = null

const todayText = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
})

const pieData = computed(() => {
  return segmentItems.value.map(item => ({
    name: item.segment_type,
    value: item.count,
  }))
})

const taskRows = computed(() => {
  const map = new Map()

  for (const task of operationTasks.value) {
    const assignee = task.assignee || '默认负责人'
    if (!map.has(assignee)) {
      map.set(assignee, {
        assignee,
        pending_confirm: 0,
        pending_execute: 0,
        completed: 0,
        failed: 0,
      })
    }

    const row = map.get(assignee)
    if (task.response_status === '待执行') row.pending_execute += 1
    else if (task.response_status === '成功') row.completed += 1
    else if (task.response_status === '失败') row.failed += 1
  }

  return Array.from(map.values()).map(row => {
    const pressureScore = row.pending_confirm + row.pending_execute + row.failed * 2
    let pressure = '低'
    if (pressureScore >= 8) pressure = '高'
    else if (pressureScore >= 4) pressure = '中'

    return {
      ...row,
      pressure,
    }
  })
})

const riskSummary = computed(() => {
  const complianceBlocked = contentDrafts.value.filter(item => item.review_status === '拦截').length
  const highRisk = contentDrafts.value.filter(item => item.review_status === '高风险待确认').length
  const frequencyBlocked = operationTasks.value.filter(item => {
    const reason = item.fail_reason || ''
    return reason.includes('频控')
  }).length

  return {
    frequencyBlocked,
    complianceBlocked,
    highRisk,
  }
})

function getPressureType(pressure) {
  const map = {
    低: 'success',
    中: 'warning',
    高: 'danger',
  }
  return map[pressure] || 'info'
}

function renderChart() {
  if (!chartRef.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: 16,
      top: 'center',
    },
    series: [
      {
        name: '人群分布',
        type: 'pie',
        radius: ['42%', '70%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: true,
        label: {
          formatter: '{b}\n{d}%',
        },
        data: pieData.value,
      },
    ],
  })
}

async function fetchOverview() {
  loading.value = true
  try {
    const [segmentRes, taskRes, draftRes] = await Promise.all([
      getSegmentDistribution(),
      getOperationTasks({ page: 1, page_size: 200 }),
      getContentDrafts({ page: 1, page_size: 200 }),
    ])

    segmentItems.value = segmentRes.data.items || []
    operationTasks.value = taskRes.data.items || []
    contentDrafts.value = draftRes.data.items || []

    await nextTick()
    renderChart()
  } catch (e) {
    ElMessage.error(e.message || '总览数据加载失败')
  } finally {
    loading.value = false
  }
}

function goCrowds() {
  router.push('/dashboard/crowds')
}

function goTasks() {
  router.push('/dashboard/tasks')
}

function goContent() {
  router.push('/dashboard/content')
}

function handleResize() {
  chartInstance?.resize()
}

onMounted(() => {
  fetchOverview()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<template>
  <div class="overview-dashboard">
    <div class="page-header">
      <div>
        <h2>私域运营总览</h2>
        <span class="page-desc">用户分层、运营任务和触达风险的集中视图</span>
      </div>
      <el-tag size="large" type="info">日期：{{ todayText }}</el-tag>
    </div>

    <div v-loading="loading">
      <el-card class="section-card clickable" @click="goCrowds">
        <template #header>
          <div class="card-header">
            <span class="section-title">人群分布</span>
            <el-button type="primary" link>查看人群</el-button>
          </div>
        </template>
        <div v-if="pieData.length" ref="chartRef" class="pie-chart" />
        <el-empty v-else description="暂无分层数据" />
      </el-card>

      <el-card class="section-card clickable" @click="goTasks">
        <template #header>
          <div class="card-header">
            <span class="section-title">任务分配</span>
            <el-button type="primary" link>查看任务</el-button>
          </div>
        </template>
        <el-table :data="taskRows" stripe style="width: 100%">
          <el-table-column prop="assignee" label="负责人" min-width="120" />
          <el-table-column prop="pending_confirm" label="待确认" width="110" />
          <el-table-column prop="pending_execute" label="待执行" width="110" />
          <el-table-column prop="completed" label="已完成" width="110" />
          <el-table-column label="触达压力" width="130">
            <template #default="{ row }">
              <el-tag :type="getPressureType(row.pressure)">{{ row.pressure }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!taskRows.length" description="暂无运营任务" />
      </el-card>

      <el-card class="section-card clickable" @click="goContent">
        <template #header>
          <div class="card-header">
            <span class="section-title">触达风险</span>
            <el-button type="primary" link>查看内容</el-button>
          </div>
        </template>
        <div class="risk-grid">
          <div class="risk-item">
            <span>频控拦截</span>
            <strong>{{ riskSummary.frequencyBlocked }}</strong>
            <small>次</small>
          </div>
          <div class="risk-item danger">
            <span>合规拦截</span>
            <strong>{{ riskSummary.complianceBlocked }}</strong>
            <small>次</small>
          </div>
          <div class="risk-item warning">
            <span>高风险待确认</span>
            <strong>{{ riskSummary.highRisk }}</strong>
            <small>条</small>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.overview-dashboard {
  min-height: 100vh;
  padding: 24px;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 6px;
  font-size: 22px;
  color: #303133;
}

.page-desc {
  color: #909399;
  font-size: 13px;
}

.section-card {
  margin-bottom: 16px;
}

.clickable {
  cursor: pointer;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-weight: 600;
  color: #303133;
}

.pie-chart {
  height: 320px;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 14px;
}

.risk-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
}

.risk-item span {
  display: block;
  margin-bottom: 8px;
  color: #909399;
}

.risk-item strong {
  margin-right: 4px;
  font-size: 30px;
  color: #409eff;
}

.risk-item.danger strong {
  color: #f56c6c;
}

.risk-item.warning strong {
  color: #e6a23c;
}

.risk-item small {
  color: #909399;
}
</style>
