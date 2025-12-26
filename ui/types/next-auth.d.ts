import NextAuth from "next-auth"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      email: string
      accessToken: string
      isPro: boolean
    }
  }

  interface User {
    id: string
    email: string
    accessToken: string
    isPro: boolean
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string
    accessToken: string
    isPro: boolean
  }
}
