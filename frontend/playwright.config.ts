import { defineConfig } from '@playwright/test'
export default defineConfig({testDir:'./tests',timeout:90000,use:{baseURL:'http://127.0.0.1:5173',headless:true},workers:1})
