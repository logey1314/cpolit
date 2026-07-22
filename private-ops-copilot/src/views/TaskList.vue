<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOperationTasks, updateOperationTaskStatus } from '../api/tasks'

const router = useRouter()

const tasks = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const activeStatus = ref('')
const loading = ref(false)
const selectedTask = ref(null)
const detailVisible = ref(false)
let timer = null

const currentAssignee = computed(() => {
  return localStorage.getItem('username') || '运营小张'
})

const pendingCount = computed(() => {
  return tasks.value.filter(item => item.response_status === '待执行').length
})

const totalPages = computed(() => {
  return Math.max(Math.ceil(total.value / pageSize.value), 1)
})

async function fetchTasks(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await getOperationTasks({
      page: currentPage.value,
      page_size: pageSize.value,
      status: activeStatus.value || undefined,
    })
    total.value = res.data.total
    tasks.value = res.data.items || []
  } catch (e) {
    if (!silent) ElMessage.error(e.message || '获取任务列表失败')
  } finally {
    if (!silent) loading.value = false
  }
}

function handleStatusChange(status) {
  activeStatus.value = status
  currentPage.value = 1
  fetchTasks()
}

function handlePageChange(page) {
  currentPage.value = page
  fetchTasks()
}

function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  fetchTasks()
}

function openDetail(row) {
  selectedTask.value = row
  detailVisible.value = true
}

async function markSuccess() {
  if (!selectedTask.value) return

  try {
    await ElMessageBox.confirm('确认将该任务标记为成功？', '标记完成', { type: 'success' })
  } catch {
    return
  }

  try {
    await updateOperationTaskStatus(selectedTask.value.task_id, '成功')
    ElMessage.success('任务已标记完成')
    detailVisible.value = false
    fetchTasks()
  } catch (e) {
    ElMessage.error(e.message || '更新任务状态失败')
  }
}

async function markFailed() {
  if (!selectedTask.value) return

  let reason = ''
  try {
    const result = await ElMessageBox.prompt('请输入失败原因', '标记失败', {
      inputType: 'textarea',
      inputPlaceholder: '例如：用户不方便接收、外部系统超时',
      confirmButtonText: '确认失败',
      cancelButtonText: '取消',
      inputValidator: value => Boolean(value && value.trim()) || '失败原因不能为空',
    })
    reason = result.value
  } catch {
    return
  }

  try {
    await updateOperationTaskStatus(selectedTask.value.task_id, '失败', reason)
    ElMessage.success('任务已标记失败')
    detailVisible.value = false
    fetchTasks()
  } catch (e) {
    ElMessage.error(e.message || '更新任务状态失败')
  }
}

function viewUser() {
  const userId = selectedTask.value?.user_id
  if (userId) {
    sessionStorage.setItem('strategyUserId', String(userId))
  }
  router.push('/dashboard/crowds')
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

function getStatusType(status) {
  const map = {
    待执行: 'warning',
    成功: 'success',
    失败: 'danger',
  }
  return map[status] || 'info'
}

function rowClassName({ row }) {
  if (row.response_status === '失败') return 'row-failed'
  if (row.response_status === '待执行') return 'row-pending'
  return ''
}

onMounted(() => {
  fetchTasks()
  timer = window.setInterval(() => fetchTasks(true), 30000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="task-list-page">
    <div class="page-header">
      <div>
        <h2>
          待办任务
          <el-badge :value="pendingCount" :hidden="pendingCount === 0" class="task-badge" />
        </h2>
        <span class="page-desc">负责人：{{ currentAssignee }}</span>
      </div>
      <el-button :loading="loading" @click="fetchTasks()">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <el-card class="filter-card">
      <el-radio-group v-model="activeStatus" @change="handleStatusChange">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="待执行">待执行</el-radio-button>
        <el-radio-button label="成功">成功</el-radio-button>
        <el-radio-button label="失败">失败</el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <span class="section-title">任务列表</span>
      </template>

      <el-table
        v-loading="loading"
        :data="tasks"
        stripe
        highlight-current-row
        :row-class-name="rowClassName"
        style="width: 100%"
      >
        <el-table-column label="用户" min-width="120">
          <template #default="{ row }">
            <span class="user-name">{{ row.user_name || `用户${row.user_id || '-'}` }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="target_system" label="系统" width="110" />
        <el-table-column prop="task_type" label="类型" width="140" />
        <el-table-column label="任务内容" min-width="360">
          <template #default="{ row }">
            <div class="task-summary">
              <div class="instruction">{{ row.task_instruction || '暂无执行说明' }}</div>
              <div class="content-preview">{{ row.content || row.request_params?.content || '暂无内容' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.response_status)">
              {{ row.response_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="计划时间" width="140">
          <template #default="{ row }">
            {{ formatTime(row.remind_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetail(row)">执行</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <span>第{{ currentPage }}页 / 共{{ totalPages }}页</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next"
          background
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="任务详情" width="720px" destroy-on-close>
      <template v-if="selectedTask">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="用户">
            {{ selectedTask.user_name || `用户${selectedTask.user_id || '-'}` }}
          </el-descriptions-item>
          <el-descriptions-item label="系统">{{ selectedTask.target_system }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedTask.task_type }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedTask.response_status)">
              {{ selectedTask.response_status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="计划时间">{{ formatTime(selectedTask.remind_time) }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ selectedTask.assignee || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="instruction-box">
          <div class="section-title">执行说明</div>
          <p>{{ selectedTask.task_instruction || '暂无执行说明' }}</p>
        </div>

        <div class="content-box">
          <div class="section-title">任务内容</div>
          <p>{{ selectedTask.content || selectedTask.request_params?.content || '暂无内容' }}</p>
        </div>

        <div v-if="selectedTask.fail_reason" class="fail-box">
          <strong>失败原因：</strong>{{ selectedTask.fail_reason }}
        </div>

        <div class="dialog-actions">
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-button @click="viewUser">查看用户</el-button>
          <el-button type="danger" plain @click="markFailed">标记失败</el-button>
          <el-button type="success" @click="markSuccess">标记完成</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.task-list-page {
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
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 6px;
  font-size: 22px;
  color: #303133;
}

.page-desc {
  color: #909399;
  font-size: 13px;
}

.filter-card,
.table-card {
  margin-bottom: 16px;
}

.section-title {
  font-weight: 600;
  color: #303133;
}

.user-name {
  font-weight: 600;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  margin-top: 16px;
  color: #606266;
}

.task-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.instruction {
  font-weight: 600;
  color: #303133;
}

.content-preview {
  line-height: 1.6;
  color: #606266;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.instruction-box,
.content-box {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
}

.instruction-box {
  background: #ecf5ff;
  border-color: #d9ecff;
}

.instruction-box p,
.content-box p {
  margin-top: 10px;
  line-height: 1.8;
  white-space: pre-wrap;
  color: #303133;
}

.fail-box {
  margin-top: 12px;
  padding: 10px;
  border-radius: 6px;
  background: #fef0f0;
  color: #f56c6c;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

:deep(.row-pending) {
  background-color: #fdf6ec !important;
}

:deep(.row-failed) {
  background-color: #fef0f0 !important;
}
</style>
