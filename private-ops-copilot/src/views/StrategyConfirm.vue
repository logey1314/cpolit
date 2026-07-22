<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { updateContentDraft } from '../api/content'
import {
  checkFrequency,
  confirmComplianceLog,
  createOperationTask,
  generateContent,
  generateStrategy,
  getContentDrafts,
  getStrategyCandidates,
  reviewContent,
  updateStrategyStatus,
} from '../api/strategy'

const strategies = ref([])
const strategyTotal = ref(0)
const strategyPage = ref(1)
const strategyPageSize = ref(10)
const strategyLoading = ref(false)
const filterStatus = ref('')
const filterKeyword = ref('')
const filterSource = ref('')
const filterSegment = ref('')
const filterChannel = ref('')

const sourceOptions = ['企微好友', '社群', '活动', '活动报名', '订单', 'CRM', '人工导入']
const segmentOptions = ['新进群', '高意向', '待培育', '沉默', '已购', '活动关注', '暂缓触达']
const channelOptions = ['私聊', '群发', '社群话题', '活动邀约', '朋友圈', '短信', '暂缓']

const generateDialogVisible = ref(false)
const generateUserId = ref(null)
const generateUserName = ref('')
const generateGoal = ref('提高转化率')
const generateLoading = ref(false)

const detailVisible = ref(false)
const detailStrategy = ref(null)
const detailContent = ref(null)
const detailFrequency = ref(null)
const detailCompliance = ref(null)
const detailLoading = ref(false)
const taskCreateLoading = ref(false)
const editVisible = ref(false)
const editContent = ref('')
const editLoading = ref(false)

async function fetchStrategies() {
  strategyLoading.value = true
  try {
    const res = await getStrategyCandidates({
      page: strategyPage.value,
      page_size: strategyPageSize.value,
      confirm_status: filterStatus.value || undefined,
      keyword: filterKeyword.value || undefined,
      source: filterSource.value || undefined,
      segment_type: filterSegment.value || undefined,
      touch_channel: filterChannel.value || undefined,
    })
    strategyTotal.value = res.data.total
    strategies.value = res.data.items
  } catch (e) {
    ElMessage.error(e.message || '获取策略列表失败')
  } finally {
    strategyLoading.value = false
  }
}

function handleFilterChange() {
  strategyPage.value = 1
  fetchStrategies()
}

function resetFilters() {
  filterStatus.value = ''
  filterKeyword.value = ''
  filterSource.value = ''
  filterSegment.value = ''
  filterChannel.value = ''
  handleFilterChange()
}

function handleStrategyPageChange(page) {
  strategyPage.value = page
  fetchStrategies()
}

function handleStrategySizeChange(size) {
  strategyPageSize.value = size
  strategyPage.value = 1
  fetchStrategies()
}

function openGenerateDialog(strategy) {
  const uid = sessionStorage.getItem('strategyUserId')

  if (strategy) {
    generateUserId.value = strategy.user_id
    generateUserName.value = strategy.user_name || `用户${strategy.user_id}`
  } else if (uid) {
    generateUserId.value = Number(uid)
    generateUserName.value = sessionStorage.getItem('strategyUserName') || `用户${uid}`
    sessionStorage.removeItem('strategyUserId')
    sessionStorage.removeItem('strategyUserName')
  } else {
    generateUserId.value = null
    generateUserName.value = ''
  }

  generateGoal.value = '提高转化率'
  generateDialogVisible.value = true
}

async function handleGenerateStrategy() {
  if (!generateUserId.value) {
    ElMessage.warning('请选择用户')
    return
  }

  generateLoading.value = true
  try {
    await generateStrategy(generateUserId.value, generateGoal.value)
    ElMessage.success('策略已生成')
    generateDialogVisible.value = false
    fetchStrategies()
  } catch (e) {
    ElMessage.error(e.message || '策略生成失败')
  } finally {
    generateLoading.value = false
  }
}

async function loadLatestOrGenerateContent(strategy) {
  const draftRes = await getContentDrafts(strategy.task_id)
  const latestDraft = draftRes.data.items[0]
  if (latestDraft) return latestDraft

  const generated = await generateContent(strategy.task_id, null)
  return generated.data
}

async function openDetail(strategy) {
  detailStrategy.value = strategy
  detailContent.value = null
  detailFrequency.value = null
  detailCompliance.value = null
  detailVisible.value = true
  detailLoading.value = true

  try {
    const content = await loadLatestOrGenerateContent(strategy)
    detailContent.value = content

    const [freqRes, complianceRes] = await Promise.all([
      checkFrequency(strategy.user_id, strategy.touch_channel),
      reviewContent(content.draft_id),
    ])

    detailFrequency.value = freqRes.data
    detailCompliance.value = complianceRes.data
  } catch (e) {
    ElMessage.error(e.message || '加载策略详情失败')
  } finally {
    detailLoading.value = false
  }
}

function getFirstComplianceLogId() {
  const risks = detailCompliance.value?.risks || []
  return risks.find(item => item.log_id)?.log_id || null
}

async function confirmHighRiskIfNeeded() {
  if (detailCompliance.value?.review_status !== '高风险待确认') return true

  try {
    await ElMessageBox.confirm(
      '当前内容为高风险待确认。确认继续后，系统会将该合规记录人工确认通过，并继续生成运营任务。',
      '高风险内容二次确认',
      { type: 'warning', confirmButtonText: '确认通过', cancelButtonText: '取消' },
    )
  } catch {
    return false
  }

  const logId = getFirstComplianceLogId()
  if (!logId) {
    ElMessage.error('未找到可确认的合规审核日志')
    return false
  }

  await confirmComplianceLog(logId, '通过', localStorage.getItem('username') || '运营人员')
  detailCompliance.value.review_status = '通过'
  return true
}

async function handleCreateTask() {
  if (!detailStrategy.value || !detailContent.value) return

  if (detailFrequency.value && !detailFrequency.value.allowed) {
    ElMessage.error('当前频控已超限，不能生成运营任务')
    return
  }

  const reviewStatus = detailCompliance.value?.review_status
  if (reviewStatus === '拦截') {
    ElMessage.error('内容合规状态为拦截，请先修改内容')
    return
  }

  try {
    const confirmed = await confirmHighRiskIfNeeded()
    if (!confirmed) return

    await ElMessageBox.confirm(
      '确认后将把策略状态改为已确认，并生成外部系统待办任务。',
      '确认并生成任务',
      { type: 'warning' },
    )
  } catch {
    return
  }

  taskCreateLoading.value = true
  try {
    await updateStrategyStatus(
      detailStrategy.value.task_id,
      '已确认',
      detailStrategy.value.assignee || '默认负责人',
    )
    await createOperationTask(detailStrategy.value.task_id, detailContent.value.draft_id)
    ElMessage.success('运营任务已生成')
    detailVisible.value = false
    fetchStrategies()
  } catch (e) {
    ElMessage.error(e.message || '任务生成失败')
  } finally {
    taskCreateLoading.value = false
  }
}

async function handleReject() {
  if (!detailStrategy.value) return

  try {
    await ElMessageBox.confirm('确认驳回该触达策略？', '驳回策略', { type: 'warning' })
  } catch {
    return
  }

  try {
    await updateStrategyStatus(detailStrategy.value.task_id, '驳回', detailStrategy.value.assignee)
    ElMessage.success('策略已驳回')
    detailVisible.value = false
    fetchStrategies()
  } catch (e) {
    ElMessage.error(e.message || '驳回失败')
  }
}

function handleEditContent() {
  if (!detailContent.value) {
    ElMessage.warning('暂无可修改的内容草稿')
    return
  }
  editContent.value = detailContent.value.content_text || ''
  editVisible.value = true
}

async function handleSaveContent() {
  if (!detailContent.value) return
  if (!editContent.value.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }

  editLoading.value = true
  try {
    const updateRes = await updateContentDraft(detailContent.value.draft_id, editContent.value)
    detailContent.value = updateRes.data

    const complianceRes = await reviewContent(detailContent.value.draft_id)
    detailCompliance.value = complianceRes.data

    ElMessage.success('内容已保存，并已重新提交合规检查')
    editVisible.value = false
  } catch (e) {
    ElMessage.error(e.message || '保存内容失败')
  } finally {
    editLoading.value = false
  }
}

function getConfirmStatusType(status) {
  const map = {
    待确认: 'warning',
    已确认: 'success',
    高风险待确认: 'danger',
    驳回: 'info',
  }
  return map[status] || 'info'
}

function getChannelType(channel) {
  const map = {
    私聊: '',
    群发: 'success',
    社群话题: 'warning',
    群公告: 'warning',
    活动邀约: 'danger',
    朋友圈: 'info',
    短信: '',
    暂缓: 'info',
  }
  return map[channel] || ''
}

function getReviewStatusType(status) {
  const map = {
    通过: 'success',
    拦截: 'danger',
    高风险待确认: 'warning',
    待审核: 'info',
    已修改: 'info',
  }
  return map[status] || 'info'
}

const complianceClass = computed(() => {
  const status = detailCompliance.value?.review_status
  return {
    blocked: status === '拦截',
    highRisk: status === '高风险待确认',
  }
})

const detailTitle = computed(() => {
  const item = detailStrategy.value
  if (!item) return '策略详情'
  return `策略详情 - ${item.user_name || `用户${item.user_id}`}`
})

onMounted(fetchStrategies)
</script>

<template>
  <div class="strategy-page">
    <div class="page-header">
      <h2>触达策略与内容确认</h2>
      <span class="page-desc">查看策略、确认内容、检查频控与合规，并生成运营任务</span>
    </div>

    <el-card class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="filterKeyword"
            placeholder="搜索用户"
            clearable
            style="width: 180px"
            @keyup.enter="handleFilterChange"
            @clear="handleFilterChange"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select
            v-model="filterStatus"
            placeholder="策略状态"
            clearable
            style="width: 160px"
            @change="handleFilterChange"
          >
            <el-option label="全部" value="" />
            <el-option label="暂无策略" value="__none__" />
            <el-option label="待确认" value="待确认" />
            <el-option label="高风险待确认" value="高风险待确认" />
            <el-option label="已确认" value="已确认" />
            <el-option label="驳回" value="驳回" />
          </el-select>
          <el-select
            v-model="filterSource"
            placeholder="来源"
            clearable
            style="width: 140px"
            @change="handleFilterChange"
          >
            <el-option v-for="item in sourceOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="filterSegment"
            placeholder="分层"
            clearable
            style="width: 140px"
            @change="handleFilterChange"
          >
            <el-option v-for="item in segmentOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-select
            v-model="filterChannel"
            placeholder="渠道"
            clearable
            style="width: 140px"
            @change="handleFilterChange"
          >
            <el-option v-for="item in channelOptions" :key="item" :label="item" :value="item" />
          </el-select>
          <el-button type="primary" @click="handleFilterChange">
            <el-icon><Filter /></el-icon>
            筛选
          </el-button>
          <el-button @click="fetchStrategies">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <span class="card-title">触达策略列表</span>
      </template>

      <el-table v-loading="strategyLoading" :data="strategies" stripe highlight-current-row>
        <el-table-column label="用户" min-width="120">
          <template #default="{ row }">
            <span class="user-name">{{ row.user_name || `用户${row.user_id}` }}</span>
            <el-tag v-if="row.user_source" size="small" type="info" class="source-tag">{{ row.user_source }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分层" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.segment_type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="渠道" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.touch_channel" :type="getChannelType(row.touch_channel)" size="small">{{ row.touch_channel }}</el-tag>
            <span v-else class="empty-text">暂无</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.task_id ? getConfirmStatusType(row.confirm_status) : 'info'" size="small">
              {{ row.task_id ? (row.confirm_status || '待确认') : '暂无策略' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="负责人" width="120">
          <template #default="{ row }">{{ row.assignee || '默认负责人' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.task_id" type="primary" link @click="openDetail(row)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button type="success" link @click="openGenerateDialog(row)">
              <el-icon><Plus /></el-icon>
              {{ row.task_id ? '新策略' : '新增策略' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="strategyPage"
          v-model:page-size="strategyPageSize"
          :total="strategyTotal"
          :page-sizes="[10, 20]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="handleStrategyPageChange"
          @size-change="handleStrategySizeChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="generateDialogVisible" title="生成触达策略" width="480px">
      <el-form label-width="90px">
        <el-form-item label="当前用户">
          <div class="selected-user">
            <span class="selected-user-name">{{ generateUserName || '未选择用户' }}</span>
            <span class="selected-user-id">ID {{ generateUserId || '-' }}</span>
          </div>
        </el-form-item>
        <el-form-item label="运营目标">
          <el-input v-model="generateGoal" placeholder="例如：提高转化率" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="generateLoading" @click="handleGenerateStrategy">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" :title="detailTitle" width="860px" destroy-on-close>
      <div v-loading="detailLoading" v-if="detailStrategy" class="detail-panel">
        <section class="detail-section">
          <div class="section-title">策略详情</div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户">
              {{ detailStrategy.user_name || `用户${detailStrategy.user_id}` }}
            </el-descriptions-item>
            <el-descriptions-item label="分层">{{ detailStrategy.segment_type || '-' }}</el-descriptions-item>
            <el-descriptions-item label="策略">
              <el-tag :type="getChannelType(detailStrategy.touch_channel)">
                {{ detailStrategy.touch_channel }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="负责人">{{ detailStrategy.assignee || '默认负责人' }}</el-descriptions-item>
            <el-descriptions-item label="理由" :span="2">
              {{ detailStrategy.strategy_reason || '暂无' }}
            </el-descriptions-item>
            <el-descriptions-item label="目标人群" :span="2">
              {{ detailStrategy.target_crowd || '暂无' }}
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-section">
          <div class="section-title">内容草稿</div>
          <div v-if="detailContent" class="content-box">
            <div class="content-text">{{ detailContent.content_text }}</div>
            <div class="content-meta">
              <el-tag size="small">{{ detailContent.content_type }}</el-tag>
              <el-tag size="small" type="info">版本 {{ detailContent.version }}</el-tag>
              <el-tag
                size="small"
                :type="detailContent.brand_tone_score >= 0.7 ? 'success' : 'warning'"
              >
                品牌语气评分 {{ detailContent.brand_tone_score }}
              </el-tag>
            </div>
            <div class="reference-box">
              <strong>引用来源：</strong>
              <template v-if="detailContent.reference_sources?.length">
                <span v-for="(ref, idx) in detailContent.reference_sources" :key="idx">
                  {{ ref.doc_name || ref.collection }}
                  <template v-if="ref.chunk_title"> &gt; {{ ref.chunk_title }}</template>
                  <template v-if="idx < detailContent.reference_sources.length - 1">；</template>
                </span>
              </template>
              <span v-else>暂无引用来源</span>
            </div>
          </div>
          <el-empty v-else description="暂无内容草稿" :image-size="60" />
        </section>

        <section class="status-grid">
          <div class="status-card" :class="{ blocked: detailFrequency && !detailFrequency.allowed }">
            <div class="section-title">频控状态</div>
            <template v-if="detailFrequency">
              <el-tag :type="detailFrequency.allowed ? 'success' : 'danger'" size="large">
                {{ detailFrequency.allowed ? '可触达' : '频控拦截' }}
              </el-tag>
              <p>
                用户窗口内已触达 {{ detailFrequency.current_count }} 次，
                上限 {{ detailFrequency.max_count }} 次。
              </p>
              <p v-if="detailFrequency.reason" class="risk-text">{{ detailFrequency.reason }}</p>
            </template>
            <el-empty v-else description="频控加载中" :image-size="50" />
          </div>

          <div class="status-card" :class="complianceClass">
            <div class="section-title">合规状态</div>
            <template v-if="detailCompliance">
              <el-tag :type="getReviewStatusType(detailCompliance.review_status)" size="large">
                {{ detailCompliance.review_status }}
              </el-tag>
              <div v-if="detailCompliance.risks?.length" class="risk-list">
                <div v-for="risk in detailCompliance.risks" :key="risk.log_id || risk.risk_detail" class="risk-row">
                  <span v-if="risk.risk_type" class="risk-type">{{ risk.risk_type }}</span>
                  <span>{{ risk.risk_detail }}</span>
                </div>
              </div>
            </template>
            <el-empty v-else description="合规加载中" :image-size="50" />
          </div>
        </section>

        <div class="dialog-actions">
          <el-button @click="handleEditContent">修改内容</el-button>
          <el-button type="danger" plain @click="handleReject">驳回</el-button>
          <el-button type="primary" :loading="taskCreateLoading" @click="handleCreateTask">
            确认并生成任务
          </el-button>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="editVisible" title="修改内容草稿" width="720px" destroy-on-close>
      <el-alert
        title="保存后会留在当前策略详情里，并重新执行合规检查。"
        type="info"
        :closable="false"
        show-icon
        class="edit-alert"
      />
      <el-input
        v-model="editContent"
        type="textarea"
        :rows="10"
        placeholder="请输入修改后的触达内容"
      />
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleSaveContent">保存并复审</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.strategy-page {
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

.toolbar-card,
.table-card {
  margin-bottom: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.card-title,
.section-title {
  font-weight: 600;
  color: #303133;
}

.user-name {
  font-weight: 600;
}

.source-tag {
  margin-left: 8px;
}

.empty-text {
  color: #c0c4cc;
  font-size: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.selected-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #f5f7fa;
}

.selected-user-name {
  font-weight: 600;
  color: #303133;
}

.selected-user-id {
  color: #909399;
  font-size: 12px;
}

.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-section,
.status-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 14px;
  background: #fff;
}

.section-title {
  margin-bottom: 12px;
}

.content-box {
  line-height: 1.8;
}

.content-text {
  white-space: pre-wrap;
  color: #303133;
  margin-bottom: 12px;
}

.content-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.reference-box {
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 4px;
  color: #606266;
  font-size: 13px;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.status-card.blocked {
  border-color: #f56c6c;
  background: #fef0f0;
}

.status-card.highRisk {
  border-color: #e6a23c;
  background: #fdf6ec;
}

.risk-text {
  color: #f56c6c;
}

.risk-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.risk-row {
  font-size: 13px;
  color: #606266;
}

.risk-type {
  display: inline-block;
  margin-right: 8px;
  color: #e6a23c;
  font-weight: 600;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 4px;
}

.edit-alert {
  margin-bottom: 12px;
}
</style>
