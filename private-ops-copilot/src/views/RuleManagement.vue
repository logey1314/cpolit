<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  confirmComplianceLog,
  getComplianceLogs,
  getFrequencyRules,
  updateFrequencyRule,
} from '../api/rules'

const activeTab = ref('forbidden')

const forbiddenWords = ref([
  { id: 1, type: '绝对', word: '全网最低价', status: '启用' },
  { id: 2, type: '绝对', word: '保证有效', status: '启用' },
  { id: 3, type: '绝对', word: '永久修复', status: '启用' },
  { id: 4, type: '需确认', word: '限时一天', status: '启用' },
])

const forbiddenDialogVisible = ref(false)
const newForbiddenType = ref('绝对')
const newForbiddenWord = ref('')

const frequencyRules = ref([])
const frequencyLoading = ref(false)
const frequencyDialogVisible = ref(false)
const editingRule = ref(null)
const editMaxCount = ref(1)
const editWindowHours = ref(24)
const editIsActive = ref(1)
const editDescription = ref('')

const complianceLogs = ref([])
const complianceTotal = ref(0)
const compliancePage = ref(1)
const compliancePageSize = ref(20)
const complianceLoading = ref(false)

const benefitRules = ref([
  { id: 1, content: '会员专享价仅对会员用户提及，不得对非会员承诺会员价。', status: '启用' },
  { id: 2, content: '限量产品必须说明限量数量和售完即止。', status: '启用' },
  { id: 3, content: '满减规则必须说明适用范围和不可叠加项。', status: '启用' },
  { id: 4, content: '赠品必须说明数量有限和先到先得。', status: '启用' },
])
const benefitDialogVisible = ref(false)
const editingBenefit = ref(null)
const benefitContent = ref('')
const benefitStatus = ref('启用')

async function loadFrequencyRules() {
  frequencyLoading.value = true
  try {
    const res = await getFrequencyRules({ page: 1, page_size: 100 })
    frequencyRules.value = res.data.items || []
  } catch (e) {
    ElMessage.error(e.message || '获取频控规则失败')
  } finally {
    frequencyLoading.value = false
  }
}

async function loadComplianceLogs() {
  complianceLoading.value = true
  try {
    const res = await getComplianceLogs({
      review_status: '高风险待确认',
      page: compliancePage.value,
      page_size: compliancePageSize.value,
    })
    complianceTotal.value = res.data.total
    complianceLogs.value = res.data.items || []
  } catch (e) {
    ElMessage.error(e.message || '获取审核队列失败')
  } finally {
    complianceLoading.value = false
  }
}

async function handleTabChange(tabName) {
  if (tabName === 'frequency') await loadFrequencyRules()
  if (tabName === 'queue') await loadComplianceLogs()
}

function openForbiddenDialog() {
  newForbiddenType.value = '绝对'
  newForbiddenWord.value = ''
  forbiddenDialogVisible.value = true
}

function addForbiddenWord() {
  if (!newForbiddenWord.value.trim()) {
    ElMessage.warning('请输入禁用词')
    return
  }

  forbiddenWords.value.push({
    id: Date.now(),
    type: newForbiddenType.value,
    word: newForbiddenWord.value.trim(),
    status: '启用',
  })
  forbiddenDialogVisible.value = false
  ElMessage.success('禁用词已新增')
}

function openBenefitDialog(row = null) {
  editingBenefit.value = row
  benefitContent.value = row?.content || ''
  benefitStatus.value = row?.status || '启用'
  benefitDialogVisible.value = true
}

function saveBenefitRule() {
  if (!benefitContent.value.trim()) {
    ElMessage.warning('请输入权益边界内容')
    return
  }

  if (editingBenefit.value) {
    editingBenefit.value.content = benefitContent.value.trim()
    editingBenefit.value.status = benefitStatus.value
    ElMessage.success('权益边界已更新')
  } else {
    benefitRules.value.push({
      id: Date.now(),
      content: benefitContent.value.trim(),
      status: benefitStatus.value,
    })
    ElMessage.success('权益边界已新增')
  }

  benefitDialogVisible.value = false
}

async function removeBenefitRule(row) {
  try {
    await ElMessageBox.confirm('确认删除该权益边界？', '删除权益边界', { type: 'warning' })
  } catch {
    return
  }

  benefitRules.value = benefitRules.value.filter(item => item.id !== row.id)
  ElMessage.success('已删除')
}

async function removeForbiddenWord(row) {
  try {
    await ElMessageBox.confirm(`确认删除禁用词「${row.word}」？`, '删除禁用词', { type: 'warning' })
  } catch {
    return
  }

  forbiddenWords.value = forbiddenWords.value.filter(item => item.id !== row.id)
  ElMessage.success('已删除')
}

function openEditRule(row) {
  editingRule.value = row
  editMaxCount.value = row.max_count
  editWindowHours.value = row.window_hours
  editIsActive.value = row.is_active
  editDescription.value = row.rule_description || ''
  frequencyDialogVisible.value = true
}

async function saveFrequencyRule() {
  if (!editingRule.value) return

  try {
    await updateFrequencyRule(editingRule.value.id, {
      max_count: editMaxCount.value,
      window_hours: editWindowHours.value,
      is_active: editIsActive.value,
      rule_description: editDescription.value,
    })
    ElMessage.success('频控规则已更新')
    frequencyDialogVisible.value = false
    loadFrequencyRules()
  } catch (e) {
    ElMessage.error(e.message || '更新频控规则失败')
  }
}

async function handleConfirmLog(row, decision) {
  const text = decision === '通过' ? '确认通过该高风险内容？' : '确认驳回并拦截该内容？'
  try {
    await ElMessageBox.confirm(text, '审核确认', { type: 'warning' })
  } catch {
    return
  }

  try {
    await confirmComplianceLog(row.log_id, decision, localStorage.getItem('username') || '规则管理员')
    ElMessage.success('审核状态已更新')
    loadComplianceLogs()
  } catch (e) {
    ElMessage.error(e.message || '审核确认失败')
  }
}

function getStatusType(status) {
  const map = {
    启用: 'success',
    停用: 'info',
    通过: 'success',
    拦截: 'danger',
    高风险待确认: 'warning',
    待审核: 'info',
  }
  return map[status] || 'info'
}

onMounted(() => {
  loadFrequencyRules()
})
</script>

<template>
  <div class="rule-management">
    <div class="page-header">
      <h2>规则管理</h2>
      <span class="page-desc">管理品牌合规规则、权益边界、频控规则和人工审核队列</span>
    </div>

    <el-card>
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="禁用词管理" name="forbidden">
          <div class="toolbar">
            <span class="section-title">禁用词管理</span>
            <el-button type="primary" @click="openForbiddenDialog">新增禁用词</el-button>
          </div>
          <el-table :data="forbiddenWords" stripe>
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="word" label="禁用词" min-width="220" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeForbiddenWord(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="权益边界" name="benefit">
          <div class="toolbar">
            <span class="section-title">权益边界</span>
            <el-button type="primary" @click="openBenefitDialog()">新增权益边界</el-button>
          </div>
          <el-table :data="benefitRules" stripe>
            <el-table-column label="边界说明" min-width="360">
              <template #default="{ row }">
                <div class="benefit-content">{{ row.content }}</div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button type="primary" link @click="openBenefitDialog(row)">编辑</el-button>
                <el-button type="danger" link @click="removeBenefitRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="频控规则" name="frequency">
          <el-table v-loading="frequencyLoading" :data="frequencyRules" stripe>
            <el-table-column prop="dimension" label="维度" width="110" />
            <el-table-column prop="dimension_id" label="目标ID" width="130" />
            <el-table-column prop="channel" label="渠道" width="110" />
            <el-table-column prop="max_count" label="最大次数" width="110" />
            <el-table-column prop="window_hours" label="时间窗口(小时)" width="140" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_active === 1 ? 'success' : 'info'">
                  {{ row.is_active === 1 ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rule_description" label="说明" min-width="180" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button type="primary" link @click="openEditRule(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="审核队列" name="queue">
          <el-table v-loading="complianceLoading" :data="complianceLogs" stripe>
            <el-table-column label="用户" width="160">
              <template #default="{ row }">
                <div class="user-cell">
                  <span class="user-name">{{ row.user_name || `用户${row.user_id || '-'}` }}</span>
                  <span class="user-meta">{{ row.user_source || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="分层/渠道" width="150">
              <template #default="{ row }">
                <div class="tag-stack">
                  <el-tag size="small">{{ row.segment_type || '-' }}</el-tag>
                  <el-tag size="small" type="info">{{ row.touch_channel || '-' }}</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="内容" min-width="260">
              <template #default="{ row }">
                <div class="content-preview">{{ row.content_text || '-' }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="risk_type" label="风险" width="130" />
            <el-table-column prop="suggestion" label="建议" min-width="220" />
            <el-table-column label="状态" width="140">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.review_status)">{{ row.review_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button type="success" link @click="handleConfirmLog(row, '通过')">确认</el-button>
                <el-button type="danger" link @click="handleConfirmLog(row, '拦截')">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="compliancePage"
              v-model:page-size="compliancePageSize"
              :total="complianceTotal"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              background
              @current-change="loadComplianceLogs"
              @size-change="loadComplianceLogs"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="forbiddenDialogVisible" title="新增禁用词" width="420px">
      <el-form label-width="80px">
        <el-form-item label="类型">
          <el-select v-model="newForbiddenType" style="width: 100%">
            <el-option label="绝对" value="绝对" />
            <el-option label="需确认" value="需确认" />
          </el-select>
        </el-form-item>
        <el-form-item label="禁用词">
          <el-input v-model="newForbiddenWord" placeholder="例如：全网最低价" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="forbiddenDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addForbiddenWord">新增</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="benefitDialogVisible" :title="editingBenefit ? '编辑权益边界' : '新增权益边界'" width="560px">
      <el-form label-width="80px">
        <el-form-item label="内容">
          <el-input
            v-model="benefitContent"
            type="textarea"
            :rows="4"
            placeholder="例如：会员专享价仅对会员用户提及，不得对非会员承诺会员价。"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="benefitStatus" style="width: 100%">
            <el-option label="启用" value="启用" />
            <el-option label="停用" value="停用" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="benefitDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveBenefitRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="frequencyDialogVisible" title="编辑频控规则" width="480px">
      <el-form label-width="110px">
        <el-form-item label="最大次数">
          <el-input-number v-model="editMaxCount" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="时间窗口">
          <el-input-number v-model="editWindowHours" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editIsActive" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editDescription" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="frequencyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveFrequencyRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.rule-management {
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

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.section-title {
  font-weight: 600;
  color: #303133;
}

.boundary-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.benefit-content {
  line-height: 1.6;
  color: #606266;
}

.user-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  font-weight: 600;
  color: #303133;
}

.user-meta {
  color: #909399;
  font-size: 12px;
}

.tag-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.content-preview {
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
