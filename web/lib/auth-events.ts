"use client"

import * as React from "react"
import { getSession } from "next-auth/react"

// Create a singleton EventBus for auth events
type AuthEvent = { type: "REAUTH_REQUIRED"; retry: (token: string) => void }
const authEvents = new Set<(event: AuthEvent) => void>()

export const emitReauth = (retry: (token: string) => void) => {
  authEvents.forEach(cb => cb({ type: "REAUTH_REQUIRED", retry }))
}

export const subscribeReauth = (cb: (event: AuthEvent) => void) => {
  authEvents.add(cb)
  return () => {
    authEvents.delete(cb)
  }
}

// Request Queue implementation
let isRefreshing = false
let requestQueue: ((token: string) => void)[] = []

export const processQueue = (token: string) => {
  requestQueue.forEach(cb => cb(token))
  requestQueue = []
  isRefreshing = false
}

export const addToQueue = (cb: (token: string) => void) => {
  requestQueue.push(cb)
}

export const setRefreshing = (val: boolean) => {
  isRefreshing = val
}

export const getIsRefreshing = () => isRefreshing
