import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 写死的用户数据：用户名、密码、角色、跳转路由
const MOCK_USERS = [
  { username: 'siyu',    password: '123456', role: 'private_ops',     roleName: '私域运营',     redirect: '/dashboard/crowds' },
  { username: 'shequn',  password: '123456', role: 'community_ops',   roleName: '社群运营',     redirect: '/dashboard/communities' },
  { username: 'neirong', password: '123456', role: 'content_ops',     roleName: '内容运营',     redirect: '/dashboard/content' },
  { username: 'fuzeren', password: '123456', role: 'manager',         roleName: '私域负责人',    redirect: '/dashboard/overview' },
  { username: 'pinpai',  password: '123456', role: 'rule_admin',      roleName: '品牌/规则管理员', redirect: '/dashboard/rules' },
]

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')
  const roleName = ref(localStorage.getItem('roleName') || '')

  const isLoggedIn = computed(() => !!token.value)

  function login(loginUsername, password) {
    const normalizedUsername = String(loginUsername || '').trim().toLowerCase()
    const normalizedPassword = String(password || '').trim()

    const user = MOCK_USERS.find(
      (u) => u.username === normalizedUsername && u.password === normalizedPassword
    )
    if (!user) {
      return { success: false, message: '用户名或密码错误' }
    }

    // 模拟 Token
    const mockToken = 'mock_token_' + user.role + '_' + Date.now()

    token.value = mockToken
    username.value = user.username
    role.value = user.role
    roleName.value = user.roleName

    localStorage.setItem('token', mockToken)
    localStorage.setItem('username', user.username)
    localStorage.setItem('role', user.role)
    localStorage.setItem('roleName', user.roleName)

    return { success: true, redirect: user.redirect }
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    roleName.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    localStorage.removeItem('roleName')
    sessionStorage.clear()
  }

  return { token, username, role, roleName, isLoggedIn, login, logout }
})
