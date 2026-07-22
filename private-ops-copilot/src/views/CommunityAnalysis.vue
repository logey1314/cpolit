<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { analyzeCommunity, filterNoiseMessages, getCommunities, getCommunityMessages } from '../api/community'

const router = useRouter()

const communityOptions = ref([])
const selectedCommunityId = ref('')
const selectedDays = ref(7)
const loading = ref(false)
const analysis = ref(null)
const noiseLoading = ref(false)
const messageLoading = ref(false)
const messages = ref([])
const messageTotal = ref(0)
const messagePage = ref(1)
const messagePageSize = ref(10)

const dayOptions = [
  { label: '全部时间', value: 0 },
  { label: '近7天', value: 7 },
  { label: '近14天', value: 14 },
  { label: '近30天', value: 30 },
]

async function fetchCommunities() {
  try {
    const res = await getCommunities()
    communityOptions.value = res.data || []
    if (!selectedCommunityId.value && communityOptions.value.length) {
      selectedCommunityId.value = communityOptions.value[0].community_id
    }
  } catch (e) {
    ElMessage.error(e.message || '获取社群列表失败')
  }
}

async function fetchAnalysis() {
  loading.value = true
  try {
    const res = await analyzeCommunity({
      community_id: selectedCommunityId.value || null,
      days: selectedDays.value,
    })
    analysis.value = res.data
  } catch (e) {
    ElMessage.error(e.message || '社群分析失败')
  } finally {
    loading.value = false
  }
}

async function fetchMessages() {
  messageLoading.value = true
  try {
    const res = await getCommunityMessages({
      community_id: selectedCommunityId.value || null,
      days: selectedDays.value,
      page: messagePage.value,
      page_size: messagePageSize.value,
    })
    messageTotal.value = res.data.total
    messages.value = res.data.items || []
  } catch (e) {
    ElMessage.error(e.message || '获取群聊消息失败')
  } finally {
    messageLoading.value = false
  }
}

async function handleRefresh() {
  await fetchAnalysis()
  await fetchMessages()
}

async function handleCommunityChange() {
  messagePage.value = 1
  await fetchAnalysis()
  await fetchMessages()
}

async function handleNoiseFilter() {
  noiseLoading.value = true
  try {
    const res = await filterNoiseMessages({
      community_id: selectedCommunityId.value || null,
      limit: 200,
    })
    ElMessage.success(`噪声过滤完成：有效 ${res.data.valid_count} 条，噪声 ${res.data.noise_count} 条`)
    messagePage.value = 1
    await fetchAnalysis()
    await fetchMessages()
  } catch (e) {
    ElMessage.error(e.message || '噪声过滤失败')
  } finally {
    noiseLoading.value = false
  }
}

function handleMessagePageChange(page) {
  messagePage.value = page
  fetchMessages()
}

function handleMessageSizeChange(size) {
  messagePageSize.value = size
  messagePage.value = 1
  fetchMessages()
}

function getIntentType(label) {
  const map = {
    需求: 'danger',
    兴趣: 'success',
    吐槽: 'warning',
    沉默: 'info',
    无关: '',
  }
  return map[label] || ''
}

function getSentimentType(sentiment) {
  const map = {
    正面: 'success',
    中性: 'info',
    负面: 'danger',
  }
  return map[sentiment] || 'info'
}

function getMessageRowClassName({ row }) {
  if (row.intent_label === '无关') return 'row-noise'
  if (row.intent_label === '沉默') return 'row-silent-message'
  if (row.intent_label === '有效') return 'row-valid-message'
  return ''
}

function formatTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

function memberRowClassName({ row }) {
  if (row.risk_level === '高') return 'row-risk'
  if ((row.silent_days || 0) >= 14) return 'row-silent'
  return ''
}

function keywordSize(count) {
  const maxCount = Math.max(...(analysis.value?.keywords || []).map(item => item.count), 1)
  return 13 + Math.round((count / maxCount) * 12)
}

function handleAdoptTopic() {
  const topic = analysis.value?.recommended_topic
  if (!topic) return

  sessionStorage.setItem('communityTopic', topic)
  sessionStorage.setItem('communityId', selectedCommunityId.value || '')
  ElMessage.success('话题已采纳，可进入策略页继续生成触达策略')
  router.push('/dashboard/strategy')
}

const structure = computed(() => {
  return analysis.value?.structure || {
    total_count: 0,
    active_count: 0,
    silent_count: 0,
    risk_count: 0,
  }
})

onMounted(async () => {
  await fetchCommunities()
  await fetchAnalysis()
  await fetchMessages()
})
</script>

<template>
  <div class="community-analysis">
    <div class="page-header">
      <h2>社群列表与互动分析</h2>
      <span class="page-desc">查看社群成员结构、互动意向、关键词热力和打扰风险</span>
    </div>

    <el-card class="filter-card">
      <div class="filter-bar">
        <div class="filter-left">
          <el-select
            v-model="selectedCommunityId"
            placeholder="选择社群"
            style="width: 220px"
            @change="handleCommunityChange"
          >
            <el-option
              v-for="item in communityOptions"
              :key="item.community_id"
              :label="item.community_name || item.community_id"
              :value="item.community_id"
            />
          </el-select>

          <el-select
            v-model="selectedDays"
            placeholder="分析时间范围"
            style="width: 150px"
            @change="handleRefresh"
          >
            <el-option v-for="item in dayOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-button type="primary" :loading="loading" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            重新分析
          </el-button>
          <el-button type="warning" :loading="noiseLoading" @click="handleNoiseFilter">
            <el-icon><Filter /></el-icon>
            执行噪声过滤
          </el-button>
        </div>
        <el-tag size="large" type="info">
          {{ analysis?.community_name || analysis?.community_id || '全部社群' }}
        </el-tag>
      </div>
    </el-card>

    <div v-loading="loading">
      <el-card class="section-card">
        <template #header>
          <span class="section-title">成员结构</span>
        </template>
        <div class="structure-grid">
          <div class="metric">
            <span class="metric-label">总人数</span>
            <strong>{{ structure.total_count }}</strong>
          </div>
          <div class="metric active">
            <span class="metric-label">活跃</span>
            <strong>{{ structure.active_count }}</strong>
          </div>
          <div class="metric silent">
            <span class="metric-label">沉默</span>
            <strong>{{ structure.silent_count }}</strong>
          </div>
          <div class="metric risk">
            <span class="metric-label">风险</span>
            <strong>{{ structure.risk_count }}</strong>
          </div>
        </div>
      </el-card>

      <el-card class="section-card">
        <template #header>
          <span class="section-title">群聊关键词热力</span>
        </template>
        <div v-if="analysis?.keywords?.length" class="keyword-cloud">
          <span
            v-for="item in analysis.keywords"
            :key="item.keyword"
            class="keyword"
            :style="{ fontSize: `${keywordSize(item.count)}px` }"
          >
            {{ item.keyword }}
            <small>{{ item.count }}</small>
          </span>
        </div>
        <el-empty v-else description="暂无关键词数据" :image-size="70" />
      </el-card>

      <el-card class="section-card">
        <template #header>
          <span class="section-title">意向分布</span>
        </template>
        <div v-if="analysis?.intent_distribution?.length" class="intent-bar">
          <el-tag
            v-for="item in analysis.intent_distribution"
            :key="item.intent_label"
            :type="getIntentType(item.intent_label)"
            size="large"
            effect="plain"
          >
            {{ item.intent_label }} {{ item.count }}
          </el-tag>
        </div>
        <el-empty v-else description="暂无意向数据" :image-size="70" />
      </el-card>

      <el-card class="section-card">
        <template #header>
          <div class="card-header-row">
            <span class="section-title">群聊消息明细</span>
            <span class="section-subtitle">可查看每条消息被过滤或识别后的状态</span>
          </div>
        </template>
        <el-table
          v-loading="messageLoading"
          :data="messages"
          stripe
          highlight-current-row
          :row-class-name="getMessageRowClassName"
          style="width: 100%"
        >
          <el-table-column label="用户" width="130">
            <template #default="{ row }">
              <span class="member-name">{{ row.user_name || `用户${row.user_id}` }}</span>
            </template>
          </el-table-column>
          <el-table-column label="消息内容" min-width="360">
            <template #default="{ row }">
              <div class="message-content">{{ row.message_content || '-' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="意向/过滤" width="120">
            <template #default="{ row }">
              <el-tag :type="getIntentType(row.intent_label)" size="small">{{ row.intent_label || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="情绪" width="100">
            <template #default="{ row }">
              <el-tag :type="getSentimentType(row.sentiment)" size="small">{{ row.sentiment || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="关键词" min-width="180">
            <template #default="{ row }">
              <div class="keyword-list">
                <el-tag v-for="keyword in row.keywords || []" :key="keyword" size="small" type="info">
                  {{ keyword }}
                </el-tag>
                <span v-if="!row.keywords?.length" class="empty-text">暂无</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="时间" width="130">
            <template #default="{ row }">{{ formatTime(row.interaction_time) }}</template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="messagePage"
            v-model:page-size="messagePageSize"
            :total="messageTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            background
            @current-change="handleMessagePageChange"
            @size-change="handleMessageSizeChange"
          />
        </div>
      </el-card>

      <el-card class="section-card">
        <template #header>
          <span class="section-title">成员列表</span>
        </template>
        <el-table
          :data="analysis?.members || []"
          stripe
          highlight-current-row
          :row-class-name="memberRowClassName"
          style="width: 100%"
        >
          <el-table-column label="昵称" min-width="120">
            <template #default="{ row }">
              <span class="member-name">{{ row.name || `用户${row.user_id}` }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="join_source" label="入群" width="110" />
          <el-table-column label="意向" width="110">
            <template #default="{ row }">
              <el-tag :type="getIntentType(row.intent_label)" size="small">{{ row.intent_label || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="情绪" width="110">
            <template #default="{ row }">
              <el-tag :type="getSentimentType(row.sentiment)" size="small">{{ row.sentiment || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="沉默天数" width="120">
            <template #default="{ row }">
              <span :class="{ 'silent-days': (row.silent_days || 0) >= 14 }">
                {{ row.silent_days ?? '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="风险" width="100">
            <template #default="{ row }">
              <el-tag :type="row.risk_level === '高' ? 'danger' : 'success'" size="small">
                {{ row.risk_level || '低' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="topic-card">
        <div class="topic-row">
          <div>
            <div class="section-title">推荐话题</div>
            <p>{{ analysis?.recommended_topic || '暂无推荐话题' }}</p>
          </div>
          <el-button type="success" :disabled="!analysis?.recommended_topic" @click="handleAdoptTopic">
            采纳
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.community-analysis {
  min-height: 100vh;
  padding: 24px;
  background: #f5f7fa;
}

.page-header {
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

.filter-card,
.section-card,
.topic-card {
  margin-bottom: 16px;
}

.filter-bar,
.filter-left,
.topic-row,
.intent-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-bar,
.topic-row {
  justify-content: space-between;
}

.section-title {
  font-weight: 600;
  color: #303133;
}

.card-header-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.section-subtitle {
  color: #909399;
  font-size: 12px;
}

.structure-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 12px;
}

.metric {
  padding: 14px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
}

.metric-label {
  display: block;
  margin-bottom: 8px;
  color: #909399;
}

.metric strong {
  font-size: 26px;
}

.metric.active strong {
  color: #67c23a;
}

.metric.silent strong {
  color: #e6a23c;
}

.metric.risk strong {
  color: #f56c6c;
}

.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.keyword {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  color: #409eff;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 6px;
  background: #ecf5ff;
}

.keyword small {
  color: #909399;
  font-size: 12px;
}

.intent-bar {
  flex-wrap: wrap;
}

.message-content {
  line-height: 1.7;
  color: #303133;
}

.keyword-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.empty-text {
  color: #c0c4cc;
  font-size: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.member-name {
  font-weight: 600;
}

.silent-days {
  color: #e6a23c;
  font-weight: 700;
}

:deep(.row-silent) {
  background-color: #fdf6ec !important;
}

:deep(.row-risk) {
  background-color: #fef0f0 !important;
}

:deep(.row-noise) {
  color: #909399;
}

:deep(.row-silent-message) {
  background-color: #fdf6ec !important;
}

:deep(.row-valid-message) {
  background-color: #f0f9eb !important;
}

.topic-row p {
  margin: 8px 0 0;
  color: #606266;
}
</style>
