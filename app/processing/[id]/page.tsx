"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Shield, Upload, Brain, CheckCircle, XCircle, AlertTriangle } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { pollJobStatus, type JobStatus } from "@/lib/job-manager"

export default function ProcessingPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.id as string

  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState("Initializing...")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) return

    const startPolling = async () => {
      try {
        await pollJobStatus(
          jobId,
          (status) => {
            setJobStatus(status)
            updateProgress(status.status)
          },
          2000, // Poll every 2 seconds
        )
      } catch (err) {
        console.error("Polling error:", err)
        setError("Failed to track job progress")
      }
    }

    startPolling()
  }, [jobId])

  const updateProgress = (status: JobStatus["status"]) => {
    switch (status) {
      case "uploaded":
        setProgress(20)
        setCurrentStep("Extracting video frames...")
        break
      case "processing":
        setProgress(60)
        setCurrentStep("Analyzing frames with AI...")
        break
      case "completed":
        setProgress(100)
        setCurrentStep("Analysis complete!")
        // Redirect to results after a short delay
        setTimeout(() => {
          router.push(`/results/${jobId}`)
        }, 2000)
        break
      case "error":
        setProgress(0)
        setCurrentStep("Processing failed")
        setError("An error occurred during processing")
        break
      default:
        setProgress(10)
        setCurrentStep("Initializing...")
    }
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" />
              Processing Error
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground">{error}</p>
            <div className="flex gap-3">
              <Button onClick={() => router.push("/")} variant="outline">
                Start Over
              </Button>
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold text-card-foreground">Processing Analysis</h1>
              <p className="text-sm text-muted-foreground">Job ID: {jobId}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-8">
          {/* Processing Status */}
          <Card>
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">Analyzing Your Video</CardTitle>
              <CardDescription>{jobStatus?.filename && `Processing: ${jobStatus.filename}`}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Progress Circle */}
              <div className="flex justify-center">
                <div className="relative w-32 h-32">
                  <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 120 120">
                    <circle
                      cx="60"
                      cy="60"
                      r="54"
                      stroke="currentColor"
                      strokeWidth="8"
                      fill="transparent"
                      className="text-muted"
                    />
                    <circle
                      cx="60"
                      cy="60"
                      r="54"
                      stroke="currentColor"
                      strokeWidth="8"
                      fill="transparent"
                      strokeDasharray={`${2 * Math.PI * 54}`}
                      strokeDashoffset={`${2 * Math.PI * 54 * (1 - progress / 100)}`}
                      className="text-primary transition-all duration-500 ease-out"
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold text-primary">{progress}%</span>
                  </div>
                </div>
              </div>

              {/* Current Step */}
              <div className="text-center space-y-2">
                <p className="text-lg font-medium text-foreground">{currentStep}</p>
                <Progress value={progress} className="w-full" />
              </div>
            </CardContent>
          </Card>

          {/* Processing Steps */}
          <Card>
            <CardHeader>
              <CardTitle>Processing Steps</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <ProcessingStep
                  icon={Upload}
                  title="Video Upload"
                  description="Video file received and validated"
                  status={progress >= 20 ? "completed" : progress > 0 ? "active" : "pending"}
                />
                <ProcessingStep
                  icon={AlertTriangle}
                  title="Frame Extraction"
                  description="Extracting frames every 2-3 seconds using FFmpeg"
                  status={progress >= 60 ? "completed" : progress >= 20 ? "active" : "pending"}
                />
                <ProcessingStep
                  icon={Brain}
                  title="AI Analysis"
                  description="Analyzing each frame for safety violations with GPT-4o"
                  status={progress >= 100 ? "completed" : progress >= 60 ? "active" : "pending"}
                />
                <ProcessingStep
                  icon={CheckCircle}
                  title="Results Ready"
                  description="Safety analysis complete with detailed findings"
                  status={progress >= 100 ? "completed" : "pending"}
                />
              </div>
            </CardContent>
          </Card>

          {/* Estimated Time */}
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-2">
                <p className="text-sm text-muted-foreground">Estimated processing time</p>
                <p className="text-lg font-semibold text-foreground">2-3 minutes</p>
                <p className="text-xs text-muted-foreground">Processing time depends on video length and complexity</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

interface ProcessingStepProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
  status: "pending" | "active" | "completed"
}

function ProcessingStep({ icon: Icon, title, description, status }: ProcessingStepProps) {
  return (
    <div className="flex items-start gap-4">
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          status === "completed"
            ? "bg-chart-5 text-white"
            : status === "active"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground"
        }`}
      >
        {status === "completed" ? (
          <CheckCircle className="h-4 w-4" />
        ) : status === "active" ? (
          <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
        ) : (
          <Icon className="h-4 w-4" />
        )}
      </div>
      <div className="space-y-1">
        <h4
          className={`font-medium ${
            status === "completed" || status === "active" ? "text-foreground" : "text-muted-foreground"
          }`}
        >
          {title}
        </h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
