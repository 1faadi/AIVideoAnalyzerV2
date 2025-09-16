import { type NextRequest, NextResponse } from "next/server"
import { getAllJobs } from "../../../lib/job-manager"

export async function GET(request: NextRequest) {
  try {
    console.log("[v0] Get all jobs API called")
    
    const jobs = getAllJobs()
    const jobsObject = jobs.reduce((acc, job) => {
      acc[job.id] = job
      return acc
    }, {} as Record<string, any>)
    
    console.log("[v0] Returning all jobs:", Object.keys(jobsObject).length)
    
    return NextResponse.json(jobsObject)
  } catch (error) {
    console.error("[v0] Get all jobs error:", error)
    return NextResponse.json({ error: "Failed to get jobs" }, { status: 500 })
  }
}
