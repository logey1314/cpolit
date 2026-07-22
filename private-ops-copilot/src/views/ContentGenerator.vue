<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  generateMultiChannelContent,
  generateSingleContent,
  getContentDrafts,
  reviewContentDraft,
  updateContentDraft,
} from '../api/content'
import { getStrategies } from '../api/strategy'

const router = useRouter()

const strategyOptions = ref([])
const selectedStrategyTaskId = ref(null)
const activityGoal = ref('7月美妆节')
const targetCrowd = ref('高意向未购')
const selectedChannels = ref(['私聊', '群公告', '朋友圈'])
const selectedProductDoc = ref('产品手册 v2.md')
const loading = ref(false)
const draftLoading = ref(false)
const drafts = ref([])

const editVisible = ref(false)
const editingDraft = ref(null)
const editingContent = ref('')
const editLoading = ref(false)

const activityOptions = [
  '7月美妆节',
  '敏感肌护理活动',
  '会员复购活动',
]

const crowdOptions = [
  '高意向未购',
  '新进群',
  '待培育',
  '活动关注',
  '已购复购',
]

const channelOptions = ['私聊', '群公告', '朋友圈', '短信']
const productDocs = ['产品手册 v2.md', '活动说明-7月美妆节.md', '品牌规范.md']

const allPassed = computed(() => {
  return drafts.value.length > 0 && drafts.value.every(item => item.review_status === '通过')
})

async function fetchStrategies() {
  try {
    const res = await getStrategies({ page: 1, page_size: 50 })
    strategyOptions.value = res.data.items || []

    const storedTaskId = sessionStorage.getItem('strategyTaskId')
    if (storedTaskId) {
      selectedStrategyTaskId.value = Number(storedTaskId)
      sessionStorage.removeItem('strategyTaskId')
    } else if (!selectedStrategyTaskId.value && strategyOptions.value.length) {
      selectedStrategyTaskId.value = strategyOptions.value[0].task_id
    }
  } catch (e) {
    ElMessage.error(e.message || '获取策略列表失败')
  }
}

async function fetchDrafts() {
  if (!selectedStrategyTaskId.value) return

  draftLoading.value = true
  try {
    const res = await getContentDrafts({
      strategy_task_id: selectedStrategyTaskId.value,
      page: 1,
      page_size: 20,
    })
    drafts.value = res.data.items || []
  } catch (e) {
    ElMessage.error(e.message || '获取内容草稿失败')
  } finally {
    draftLoading.value = false
  }
}

async function handleStrategyChange() {
  await fetchDrafts()
}

async function handleGenerate() {
  if (!selectedStrategyTaskId.value) {
    ElMessage.warning('请选择关联策略')
    return
  }

  if (!selectedChannels.value.length) {
    ElMessage.warning('请选择至少一个触达渠道')
    return
  }

  loading.value = true
  try {
    const res = await generateMultiChannelContent({
      strategy_task_id: selectedStrategyTaskId.value,
      channels: selectedChannels.value,
    })
    drafts.value = res.data.drafts || []
    ElMessage.success('多渠道内容已生成')
  } catch (e) {
    ElMessage.error(e.message || '内容生成失败')
  } finally {
    loading.value = false
  }
}

function openEdit(draft) {
  editingDraft.value = draft
  editingContent.value = draft.content_text || ''
  editVisible.value = true
}

async function handleSaveEdit() {
  if (!editingDraft.value) return

  editLoading.value = true
  try {
    const res = await updateContentDraft(editingDraft.value.draft_id, editingContent.value)
    const index = drafts.value.findIndex(item => item.draft_id === editingDraft.value.draft_id)
    if (index >= 0) drafts.value[index] = res.data
    ElMessage.success('内容已保存，合规状态已回到待审核')
    editVisible.value = false
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    editLoading.value = false
  }
}

function contentTypeToChannel(contentType) {
  const map = {
    私聊话术: '私聊',
    群公告: '群公告',
    朋友圈文案: '朋友圈',
    短信短句: '短信',
  }
  return map[contentType] || '私聊'
}

async function handleRegenerate(draft) {
  try {
    await ElMessageBox.confirm('确认重新生成该渠道内容？新内容会生成一个新版本草稿。', '重新生成', {
      type: 'warning',
    })
  } catch {
    return
  }

  loading.value = true
  try {
    const res = await generateSingleContent(selectedStrategyTaskId.value, draft.content_type)
    drafts.value.unshift(res.data)
    ElMessage.success(`${contentTypeToChannel(draft.content_type)}内容已重新生成`)
  } catch (e) {
    ElMessage.error(e.message || '重新生成失败')
  } finally {
    loading.value = false
  }
}

async function handleReviewOne(draft) {
  try {
    const res = await reviewContentDraft(draft.draft_id)
    draft.review_status = res.data.review_status
    draft.risks = res.data.risks || []
    ElMessage.success('合规检查完成')
  } catch (e) {
    ElMessage.error(e.message || '合规检查失败')
  }
}

async function handleReviewAll() {
  if (!drafts.value.length) {
    ElMessage.warning('暂无内容草稿')
    return
  }

  loading.value = true
  try {
    for (const draft of drafts.value) {
      const res = await reviewContentDraft(draft.draft_id)
      draft.review_status = res.data.review_status
      draft.risks = res.data.risks || []
    }
    ElMessage.success('全部草稿已提交合规检查')
  } catch (e) {
    ElMessage.error(e.message || '合规检查失败')
  } finally {
    loading.value = false
  }
}

function handleHandOff() {
  if (!allPassed.value) {
    ElMessage.warning('只有全部通过后才能交给运营执行')
    return
  }

  sessionStorage.setItem('strategyTaskId', String(selectedStrategyTaskId.value))
  ElMessage.success('已交给运营执行，跳转到策略确认页')
  router.push('/dashboard/strategy')
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

function rowClassName({ row }) {
  if (row.review_status === '拦截') return 'row-blocked'
  if (row.review_status === '高风险待确认') return 'row-warning'
  return ''
}

onMounted(async () => {
  await fetchStrategies()
  await fetchDrafts()
})
</script>

<template>
  <div class="content-generator">
    <div class="page-header">
      <h2>内容生成工作台</h2>
      <span class="page-desc">生成多渠道内容草稿，完成品牌合规检查后交给运营执行</span>
    </div>

    <el-card class="form-card">
      <div class="form-grid">
        <el-form-item label="关联策略">
          <el-select
            v-model="selectedStrategyTaskId"
            placeholder="选择触达策略"
            filterable
            style="width: 240px"
            @change="handleStrategyChange"
          >
            <el-option
              v-for="item in strategyOptions"
              :key="item.task_id"
              :label="`${item.user_name || `用户${item.user_id}`} / ${item.segment_type || '-'} / ${item.touch_channel}`"
              :value="item.task_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="活动目标">
          <el-select v-model="activityGoal" style="width: 180px">
            <el-option v-for="item in activityOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>

        <el-form-item label="目标人群">
          <el-select v-model="targetCrowd" style="width: 180px">
            <el-option v-for="item in crowdOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>

        <el-form-item label="产品资料">
          <el-select v-model="selectedProductDoc" style="width: 220px">
            <el-option v-for="item in productDocs" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
      </div>

      <div class="channel-row">
        <span class="channel-label">触达渠道</span>
        <el-checkbox-group v-model="selectedChannels">
          <el-checkbox v-for="item in channelOptions" :key="item" :label="item">{{ item }}</el-checkbox>
        </el-checkbox-group>
        <el-button type="primary" :loading="loading" @click="handleGenerate">
          <el-icon><MagicStick /></el-icon>
          生成
        </el-button>
      </div>
    </el-card>

    <el-card class="draft-card">
      <template #header>
        <div class="card-header">
          <span class="section-title">内容草稿</span>
          <div class="header-actions">
            <el-button :disabled="!drafts.length" @click="handleReviewAll">提交合规检查</el-button>
            <el-button type="success" :disabled="!allPassed" @click="handleHandOff">交给运营执行</el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="draftLoading || loading"
        :data="drafts"
        stripe
        :row-class-name="rowClassName"
        style="width: 100%"
      >
        <el-table-column label="渠道" width="110">
          <template #default="{ row }">
            <el-tag>{{ contentTypeToChannel(row.content_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="内容" min-width="360">
          <template #default="{ row }">
            <div class="content-preview">{{ row.content_text }}</div>
            <div v-if="row.risks?.length" class="risk-hints">
              <div v-for="risk in row.risks" :key="risk.log_id || risk.risk_detail">
                <strong>{{ risk.risk_type || '提示' }}：</strong>{{ risk.suggestion || risk.risk_detail }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="评分" width="100">
          <template #default="{ row }">
            <el-tag :type="row.brand_tone_score >= 0.7 ? 'success' : 'warning'">
              {{ row.brand_tone_score }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag :type="getReviewStatusType(row.review_status)">
              {{ row.review_status || '待审核' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
            <el-button type="warning" link @click="handleRegenerate(row)">重新生成</el-button>
            <el-button type="success" link @click="handleReviewOne(row)">检查</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!draftLoading && !drafts.length" description="暂无内容草稿，请先生成" />
    </el-card>

    <el-card class="result-card">
      <span class="section-title">合规检查结果：</span>
      <template v-if="allPassed">
        <el-tag type="success" size="large">全部通过</el-tag>
        <el-button type="success" @click="handleHandOff">交给运营执行</el-button>
      </template>
      <template v-else-if="drafts.some(item => item.review_status === '拦截')">
        <el-tag type="danger" size="large">存在拦截内容</el-tag>
      </template>
      <template v-else-if="drafts.some(item => item.review_status === '高风险待确认')">
        <el-tag type="warning" size="large">存在高风险待确认</el-tag>
      </template>
      <template v-else>
        <el-tag type="info" size="large">待检查</el-tag>
      </template>
    </el-card>

    <el-dialog v-model="editVisible" title="编辑内容草稿" width="680px">
      <el-input
        v-model="editingContent"
        type="textarea"
        :rows="10"
        placeholder="请输入内容"
      />
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.content-generator {
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

.form-card,
.draft-card,
.result-card {
  margin-bottom: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 12px;
}

.channel-row,
.card-header,
.header-actions,
.result-card {
  display: flex;
  align-items: center;
  gap: 12px;
}

.channel-row {
  margin-top: 10px;
}

.channel-label,
.section-title {
  font-weight: 600;
  color: #303133;
}

.card-header {
  justify-content: space-between;
}

.content-preview {
  line-height: 1.7;
  color: #303133;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.risk-hints {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 12px;
  line-height: 1.6;
}

:deep(.row-blocked) {
  background-color: #fef0f0 !important;
}

:deep(.row-warning) {
  background-color: #fdf6ec !important;
}
</style>
