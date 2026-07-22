import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard/crowds',
    name: 'Crowds',
    component: () => import('../views/CrowdDashboard.vue'),
    meta: { requiresAuth: true, role: 'private_ops' }
  },
  {
    path: '/dashboard/strategy',
    name: 'Strategy',
    component: () => import('../views/StrategyConfirm.vue'),
    meta: { requiresAuth: true, role: 'private_ops' }
  },
  {
    path: '/dashboard/communities',
    name: 'Communities',
    component: () => import('../views/CommunityAnalysis.vue'),
    meta: { requiresAuth: true, role: 'community_ops' }
  },
  {
    path: '/dashboard/content',
    name: 'Content',
    component: () => import('../views/ContentGenerator.vue'),
    meta: { requiresAuth: true, role: 'content_ops' }
  },
  {
    path: '/dashboard/overview',
    name: 'Overview',
    component: () => import('../views/OverviewDashboard.vue'),
    meta: { requiresAuth: true, role: 'manager' }
  },
  {
    path: '/dashboard/rules',
    name: 'Rules',
    component: () => import('../views/RuleManagement.vue'),
    meta: { requiresAuth: true, role: 'rule_admin' }
  },
  {
    path: '/dashboard/tasks',
    name: 'Tasks',
    component: () => import('../views/TaskList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：检查 Token 和角色权限
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')

  // 访问登录页时，已登录则跳转对应工作面
  if (to.path === '/login') {
    if (token && role) {
      const roleRedirectMap = {
        'private_ops': '/dashboard/crowds',
        'community_ops': '/dashboard/communities',
        'content_ops': '/dashboard/content',
        'manager': '/dashboard/overview',
        'rule_admin': '/dashboard/rules',
      }
      next(roleRedirectMap[role] || '/dashboard/tasks')
    } else {
      next()
    }
    return
  }

  // 需要登录的页面
  if (to.meta.requiresAuth) {
    if (!token) {
      next('/login')
      return
    }
    // 检查角色权限（tasks 页所有角色可访问）
    if (to.meta.role && to.meta.role !== role) {
      next('/login')
      return
    }
  }

  next()
})

export default router
