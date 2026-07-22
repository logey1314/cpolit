<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUsers, getUserSegment, getUserIdentities, standardizeUserTags, adjustSegment, importMockUsers } from '../api/crowds'

// ========== filter ==========
const sourceOptions = [
  { label: "全部来源", value: "" },
  { label: "企微好友", value: "企微好友" },
  { label: "社群", value: "社群" },
  { label: "活动", value: "活动" },
  { label: "CRM", value: "CRM" },
  { label: "人工导入", value: "人工导入" },
]

const segmentOptions = [
  { label: "全部分层", value: "" },
  { label: "新进群", value: "新进群" },
  { label: "高意向", value: "高意向" },
  { label: "待培育", value: "待培育" },
  { label: "沉默", value: "沉默" },
  { label: "已购", value: "已购" },
  { label: "活动关注", value: "活动关注" },
  { label: "暂缓触达", value: "暂缓触达" },
]

const selectedSource = ref("")
const selectedSegment = ref("")
const searchKeyword = ref("")
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const users = ref([])
const loading = ref(false)

const mockImportVisible = ref(false)
const mockImportSource = ref("企微好友")
const mockImportScenario = ref("企微好友")
const mockImportLoading = ref(false)

const mockImportScenarios = {
  "企微好友": [
    {
      external_user_id: "mock_qw_101",
      phone: "13800002001",
      name: "模拟小周",
      source: "企微好友",
      tags: ["护肤", "高意向"],
      purchase_status: "未购",
      operation_status: "重点",
    },
    {
      external_user_id: "mock_qw_102",
      phone: "13800002002",
      name: "模拟阿晴",
      source: "企微好友",
      tags: ["敏感肌", "咨询价格"],
      purchase_status: "未购",
      operation_status: "正常",
    },
  ],
  "活动报名": [
    {
      external_user_id: "mock_act_201",
      phone: "13800002003",
      name: "模拟丽丽",
      source: "活动报名",
      tags: ["美妆", "活动关注"],
      purchase_status: "未购",
      operation_status: "正常",
    },
    {
      external_user_id: "mock_act_202",
      phone: "13800002002",
      name: "模拟阿晴-活动",
      source: "活动报名",
      tags: ["活动积极", "优惠关注"],
      purchase_status: "未购",
      operation_status: "正常",
    },
  ],
  "订单": [
    {
      external_user_id: "mock_order_301",
      phone: "13800002004",
      name: "模拟陈姐",
      source: "订单",
      tags: ["已购", "复购潜力"],
      purchase_status: "已购",
      operation_status: "正常",
    },
    {
      external_user_id: "mock_order_302",
      phone: "13800002005",
      name: "模拟老刘",
      source: "订单",
      tags: ["电子", "已收货"],
      purchase_status: "复购",
      operation_status: "正常",
    },
  ],
  "CRM": [
    {
      external_user_id: "mock_crm_401",
      phone: "13800002006",
      name: "模拟张姐",
      source: "CRM",
      tags: ["重点客户", "高消费"],
      purchase_status: "已购",
      operation_status: "重点",
    },
    {
      external_user_id: "mock_crm_402",
      phone: "13800002007",
      name: "模拟小赵",
      source: "CRM",
      tags: ["退群风险", "沉默"],
      purchase_status: "未购",
      operation_status: "暂缓",
    },
  ],
  "人工导入": [
    {
      external_user_id: "mock_manual_501",
      phone: "13800002008",
      name: "模拟阿杰",
      source: "人工导入",
      tags: ["健身", "低活跃"],
      purchase_status: "未购",
      operation_status: "暂缓",
    },
    {
      external_user_id: "mock_manual_502",
      phone: "13800002009",
      name: "模拟小林",
      source: "人工导入",
      tags: ["母婴", "新手"],
      purchase_status: "未购",
      operation_status: "正常",
    },
  ],
}

const mockImportUsers = computed(() => mockImportScenarios[mockImportScenario.value] || [])

// ========== segment stats ==========
const segmentStats = reactive({})

// ========== segment cache ==========
const userSegments = ref({})
const segmentLoading = ref({})
const displayedUsers = computed(() => {
  return users.value.map(u => ({
    ...u,
    segment: userSegments.value[u.id] || null,
  }))
})

function computeStats() {
  const stats = {}
  for (const u of displayedUsers.value) {
    const seg = u.segment ? (u.segment.segment_type || "未知") : "未分层"
    stats[seg] = (stats[seg] || 0) + 1
  }
  Object.keys(segmentStats).forEach(k => delete segmentStats[k])
  Object.assign(segmentStats, stats)
}

async function loadUserSegments(userList) {
  const ids = userList.map(u => u.id)
  for (const id of ids) {
    if (userSegments.value[id] || segmentLoading.value[id]) continue
    segmentLoading.value[id] = true
    try {
      const res = await getUserSegment(id)
      userSegments.value[id] = res.data
    } catch {
      userSegments.value[id] = null
    } finally {
      segmentLoading.value[id] = false
    }
  }
}
async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUsers({
      page: currentPage.value,
      size: pageSize.value,
      source: selectedSource.value || undefined,
      keyword: searchKeyword.value || undefined,
      segment_type: selectedSegment.value || undefined,
    })
    total.value = res.data.total
    users.value = res.data.items
    await loadUserSegments(res.data.items)
    computeStats()
  } catch (e) {
    ElMessage.error(e.message || '获取用户列表失败，请确认后端服务已启动')
  } finally {
    loading.value = false
  }
}
// ========== pagination ==========
function handlePageChange(page) {
  currentPage.value = page
  fetchUsers()
}

function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  fetchUsers()
}

function handleFilter() {
  currentPage.value = 1
  fetchUsers()
}

function handleRefresh() {
  userSegments.value = {}
  fetchUsers()
}

function openMockImport() {
  mockImportSource.value = selectedSource.value || "企微好友"
  mockImportScenario.value = mockImportSource.value
  mockImportVisible.value = true
}

function handleMockScenarioChange(value) {
  mockImportSource.value = value
}

async function handleImportMockUsers() {
  const users = mockImportUsers.value
  if (!users.length) {
    ElMessage.warning("请选择模拟数据")
    return
  }

  mockImportLoading.value = true
  try {
    const res = await importMockUsers({
      source: mockImportSource.value,
      users,
    })
    const errors = res.data.errors || []
    if (errors.length) {
      ElMessage.warning(`导入 ${res.data.imported_count} 条，失败 ${errors.length} 条`)
    } else {
      ElMessage.success(`成功导入 ${res.data.imported_count} 条模拟用户`)
    }
    mockImportVisible.value = false
    userSegments.value = {}
    currentPage.value = 1
    await fetchUsers()
  } catch (e) {
    ElMessage.error(e.message || "导入模拟用户失败")
  } finally {
    mockImportLoading.value = false
  }
}

function handleSegmentFilter(segmentType) {
  selectedSegment.value = segmentType
  handleFilter()
}

// ========== detail dialog ==========
const detailVisible = ref(false)
const detailUser = ref(null)
const identityGroup = ref(null)
const identityLoading = ref(false)
const tagStandardizeLoading = ref(false)

async function loadIdentityGroup(userId) {
  identityGroup.value = null
  identityLoading.value = true
  try {
    const res = await getUserIdentities(userId)
    identityGroup.value = res.data
  } catch (e) {
    ElMessage.error(e.message || "获取身份归并记录失败")
  } finally {
    identityLoading.value = false
  }
}

async function openDetail(user) {
  detailUser.value = user
  detailVisible.value = true
  await loadIdentityGroup(user.id)
}

async function handleStandardizeTags() {
  if (!detailUser.value) return

  tagStandardizeLoading.value = true
  try {
    const res = await standardizeUserTags(detailUser.value.id)
    ElMessage.success(`标签已标准化：${(res.data.updated_tags || []).join("、")}`)
    await fetchUsers()
    const updatedUser = users.value.find(item => item.id === detailUser.value.id)
    if (updatedUser) {
      detailUser.value = {
        ...updatedUser,
        segment: userSegments.value[updatedUser.id] || detailUser.value.segment,
      }
    }
    await loadIdentityGroup(detailUser.value.id)
  } catch (e) {
    ElMessage.error(e.message || "标签标准化失败")
  } finally {
    tagStandardizeLoading.value = false
  }
}

// ========== adjust segment ==========
const adjustSegmentType = ref("")
const adjustReason = ref("")
const adjustLoading = ref(false)

async function handleAdjustSegment() {
  if (!adjustSegmentType.value) {
    ElMessage.warning("请选择目标分层")
    return
  }
  adjustLoading.value = true
  try {
    await adjustSegment(detailUser.value.id, { segment_type: adjustSegmentType.value, reason: adjustReason.value || "人工调整" })
    ElMessage.success("分层已调整")
    const res = await getUserSegment(detailUser.value.id)
    userSegments.value[detailUser.value.id] = res.data
    detailUser.value.segment = res.data
    adjustSegmentType.value = ""
    adjustReason.value = ""
    computeStats()
  } catch (e) {
    ElMessage.error(e.message || "调整失败，请确认后端服务已启动")
  } finally {
    adjustLoading.value = false
  }
}

function goToStrategy(user) {
  sessionStorage.setItem("strategyUserId", user.id)
  sessionStorage.setItem("strategyUserName", user.name || "")
  const resolved = window.__router__
  if (resolved) { resolved.push("/dashboard/strategy") }
  else { window.location.href = "/dashboard/strategy" }
}

function getSegmentType(seg) {
  const map = { "高意向": "danger", "新进群": "success", "已购": "", "待培育": "warning", "沉默": "info", "活动关注": "success", "暂缓触达": "info" }
  return map[seg] || "info"
}

function tableRowClassName({ row }) {
  const seg = row.segment
  if (seg && seg.confidence_score < 0.6) return "row-warning"
  return ""
}

function confidencePercent(segment) {
  return Math.round((segment.confidence_score || 0) * 100)
}

function confidenceStatus(segment) {
  const score = segment.confidence_score || 0
  if (score >= 0.8) return "success"
  if (score >= 0.6) return ""
  return "warning"
}

const detailTitle = computed(() => {
  return '分层详情 - ' + (detailUser.value ? (detailUser.value.name || '') : '')
})

onMounted(() => { fetchUsers() })
</script>
<template>
  <div class="crowd-dashboard">
    <div class="page-header">
      <h2>人群选择与分层看板</h2>
      <span class="page-desc">私域运营工作台 - 查看和管理用户分层</span>
    </div>

    <el-card class="filter-card">
      <div class="filter-bar">
        <div class="filter-left">
          <el-select v-model="selectedSource" placeholder="来源筛选" clearable style="width: 140px" @change="handleFilter">
            <el-option v-for="opt in sourceOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-select v-model="selectedSegment" placeholder="分层筛选" clearable style="width: 140px" @change="handleFilter">
            <el-option v-for="opt in segmentOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-input v-model="searchKeyword" placeholder="搜索昵称..." clearable style="width: 200px" @input="computeStats">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" @click="handleFilter"><el-icon><Filter /></el-icon> 筛选</el-button>
          <el-button @click="handleRefresh"><el-icon><Refresh /></el-icon> 刷新</el-button>
          <el-button type="success" @click="openMockImport"><el-icon><Upload /></el-icon> 导入模拟用户</el-button>
        </div>
        <div class="filter-right">
          <el-tag size="large" type="info">共 <strong>{{ total }}</strong> 人</el-tag>
        </div>
      </div>
    </el-card>
    <el-card class="stats-card">
      <template #header><span class="stats-title">分层统计</span></template>
      <div class="stats-bar">
        <div v-for="(count, segType) in segmentStats" :key="segType" class="stat-item" :class="{ active: selectedSegment === segType }" @click="handleSegmentFilter(segType)">
          <el-tag :type="getSegmentType(segType)" size="large" effect="plain" class="stat-tag">{{ segType }} <span class="stat-count">{{ count }}</span></el-tag>
        </div>
        <div v-if="Object.keys(segmentStats).length === 0" class="stat-empty">暂无分层数据</div>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table v-loading="loading" :data="displayedUsers" stripe highlight-current-row style="width: 100%" :row-class-name="tableRowClassName">
        <el-table-column prop="name" label="昵称" min-width="100">
          <template #default="{ row }"><span class="user-name">{{ row.name }}</span></template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.source }}</el-tag></template>
        </el-table-column>
        <el-table-column label="标签" min-width="220">
          <template #default="{ row }">
            <div class="tag-list">
              <el-tag v-for="tag in row.tags || []" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
              <span v-if="!row.tags?.length" class="empty-text">暂无</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="分层" width="130">
          <template #default="{ row }">
            <template v-if="row.segment">
              <el-tag :type="getSegmentType(row.segment.segment_type)" size="small">{{ row.segment.segment_type }}</el-tag>
              <span v-if="row.segment.manual_adjusted" class="manual-badge"><el-icon><Edit /></el-icon></span>
            </template>
            <el-tag v-else type="info" size="small"><el-icon><Loading /></el-icon> 加载中</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触达优先级" width="120" align="center">
          <template #default="{ row }">
            <template v-if="row.segment">
              <el-rate :model-value="row.segment.touch_priority" :max="5" disabled show-score text-color="#409eff" />
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>        <el-table-column label="置信度" width="110" align="center">
          <template #default="{ row }">
            <template v-if="row.segment">
              <el-progress :percentage="confidencePercent(row.segment)" :stroke-width="6" :show-text="true" :status="confidenceStatus(row.segment)" />
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDetail(row)"><el-icon><View /></el-icon> 查看</el-button>
            <el-button v-if="row.segment" type="success" link size="small" @click="goToStrategy(row)">策略</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" background @current-change="handlePageChange" @size-change="handleSizeChange" />
      </div>
    </el-card>
    <el-dialog v-model="detailVisible" :title="detailTitle" width="900px" destroy-on-close>
      <template v-if="detailUser && detailUser.segment">
        <el-descriptions :column="2" border size="large">
          <el-descriptions-item label="当前分层">
            <el-tag :type="getSegmentType(detailUser.segment.segment_type)" size="large">{{ detailUser.segment.segment_type }}</el-tag>
            <span v-if="detailUser.segment.manual_adjusted" class="manual-badge"><el-icon><Edit /></el-icon> 人工调整</span>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            <el-progress :percentage="confidencePercent(detailUser.segment)" style="width: 80%" :stroke-width="8" :status="confidenceStatus(detailUser.segment)" />
          </el-descriptions-item>
          <el-descriptions-item label="分层依据" :span="2">{{ detailUser.segment.segment_basis || "暂无" }}</el-descriptions-item>
          <el-descriptions-item label="触达优先级" :span="2">
            <el-rate :model-value="detailUser.segment.touch_priority" :max="5" disabled show-score />
          </el-descriptions-item>
          <el-descriptions-item label="适用策略" :span="2">{{ detailUser.segment.applicable_strategy || "通用运营跟进" }}</el-descriptions-item>
          <el-descriptions-item label="当前标签" :span="2">
            <div class="detail-tags">
              <el-tag v-for="tag in detailUser.tags || []" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
              <span v-if="!detailUser.tags?.length" class="empty-text">暂无标签</span>
              <el-button
                type="primary"
                plain
                size="small"
                :loading="tagStandardizeLoading"
                @click="handleStandardizeTags"
              >
                标准化标签
              </el-button>
            </div>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">身份归并记录</el-divider>
        <div v-loading="identityLoading" class="identity-area">
          <el-alert
            v-if="identityGroup?.main_user"
            :title="`主用户：${identityGroup.main_user.name || '未命名'}（ID ${identityGroup.main_user.id}，手机号 ${identityGroup.main_user.phone || '-'}）`"
            type="success"
            :closable="false"
            show-icon
            class="identity-alert"
          />
          <el-table :data="identityGroup?.records || []" border stripe size="small">
            <el-table-column prop="id" label="记录ID" width="80" />
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column prop="phone" label="手机号" width="130" />
            <el-table-column label="来源" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ row.source || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="external_user_id" label="外部ID" min-width="140" />
            <el-table-column label="merged_user_id" width="130">
              <template #default="{ row }">
                <el-tag v-if="row.merged_user_id" type="warning" size="small">{{ row.merged_user_id }}</el-tag>
                <el-tag v-else type="success" size="small">主用户</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="标签" min-width="180">
              <template #default="{ row }">
                <el-tag v-for="tag in row.tags || []" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-divider content-position="left">人工调整分层</el-divider>
        <div class="adjust-area">
          <el-select v-model="adjustSegmentType" placeholder="选择目标分层" style="width: 180px; margin-right: 12px">
            <el-option v-for="opt in segmentOptions.filter(o => o.value)" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-input v-model="adjustReason" placeholder="调整原因（可选）" style="width: 220px; margin-right: 12px" />
          <el-button type="warning" :loading="adjustLoading" @click="handleAdjustSegment">确认调整</el-button>
        </div>

        <el-divider content-position="left">下一步操作</el-divider>
        <div class="action-area">
          <el-button type="primary" size="large" @click="goToStrategy(detailUser)"><el-icon><MagicStick /></el-icon> 生成触达策略</el-button>
          <span class="action-hint">触达策略将在 <strong>触达策略与内容确认</strong> 页面生成</span>
        </div>
      </template>
      <template v-else><el-empty description="该用户暂无分层数据"><el-button type="primary" @click="detailVisible = false">关闭</el-button></el-empty></template>
    </el-dialog>

    <el-dialog v-model="mockImportVisible" title="导入模拟用户数据" width="760px" destroy-on-close>
      <el-alert
        title="这里使用前端内置模拟数据调用 POST /api/v1/users/import，导入后会刷新用户列表。"
        type="info"
        :closable="false"
        show-icon
        class="import-alert"
      />
      <el-form label-width="90px" class="import-form">
        <el-form-item label="数据场景">
          <el-select v-model="mockImportScenario" style="width: 260px" @change="handleMockScenarioChange">
            <el-option v-for="(_, name) in mockImportScenarios" :key="name" :label="name" :value="name" />
          </el-select>
        </el-form-item>
        <el-form-item label="写入来源">
          <el-select v-model="mockImportSource" style="width: 260px">
            <el-option v-for="opt in sourceOptions.filter(item => item.value)" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="mockImportUsers" border stripe size="small">
        <el-table-column prop="name" label="昵称" width="120" />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="source" label="原始来源" width="110" />
        <el-table-column label="标签" min-width="220">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="purchase_status" label="购买" width="90" />
        <el-table-column prop="operation_status" label="运营" width="90" />
      </el-table>

      <template #footer>
        <el-button @click="mockImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="mockImportLoading" @click="handleImportMockUsers">
          确认导入 {{ mockImportUsers.length }} 条
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
<style scoped>
.crowd-dashboard { padding: 24px; background: #f5f7fa; min-height: 100vh; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #303133; margin: 0 0 4px; }
.page-desc { font-size: 13px; color: #909399; }
.filter-card { margin-bottom: 16px; }
.filter-bar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.filter-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.stats-card { margin-bottom: 16px; }
.stats-title { font-weight: 600; font-size: 15px; }
.stats-bar { display: flex; flex-wrap: wrap; gap: 12px; }
.stat-item { cursor: pointer; transition: transform 0.15s; }
.stat-item:hover { transform: scale(1.06); }
.stat-item.active { opacity: 0.6; }
.stat-tag { cursor: pointer; font-size: 14px; padding: 6px 14px; }
.stat-count { font-weight: 700; margin-left: 4px; font-size: 16px; }
.stat-empty { color: #c0c4cc; font-size: 14px; }
.table-card { margin-bottom: 16px; }
.user-name { font-weight: 600; color: #303133; }
.tag-list,
.detail-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.empty-text { color: #c0c4cc; font-size: 12px; }
.manual-badge { display: inline-flex; align-items: center; margin-left: 4px; color: #e6a23c; font-size: 12px; }
:deep(.row-warning) { background-color: #fdf6ec !important; }
.pagination-bar { display: flex; justify-content: flex-end; margin-top: 16px; }
.identity-area { margin-bottom: 8px; }
.identity-alert { margin-bottom: 12px; }
.adjust-area { display: flex; align-items: center; margin-bottom: 8px; }
.action-area { display: flex; align-items: center; gap: 16px; }
.action-hint { font-size: 13px; color: #909399; }
.import-alert { margin-bottom: 16px; }
.import-form { margin-bottom: 12px; }
.tag-item { margin-right: 4px; margin-bottom: 4px; }
</style>
