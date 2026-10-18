import { defineConfig } from '@playwright/test'
export default defineConfig({testDir:'./tests',timeout:90000,use:{baseURL:process.env.STK_BROWSER_BASE_URL??'http://127.0.0.1:5173',headless:true},workers:1})
