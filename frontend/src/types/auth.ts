export type UserRole = 'teacher' | 'student' | 'admin'

export interface User {
  id: string
  username: string
  name: string
  role: UserRole
}
