"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Shield, Brain, CheckCircle, XCircle, ArrowLeft, Play, Image as ImageIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { type JobStatus } from "@/lib/job-manager"

export default function FramesPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.id as string

  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}`)
        if (!response.ok) {
          throw new Error(`Failed to fetch job: ${response.statusText}`)
        }
        
        const status = await response.json()
        setJobStatus(status)
      } catch (err) {
        setError("Failed to load job data")
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    if (jobId) {
      fetchJob()
    }
  }, [jobId])

  const handleStartAnalysis = async () => {
    if (!jobStatus) return

    setIsAnalyzing(true)
    try {
      const response = await fetch(`/api/analyze/${jobId}`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error("Analysis failed")
      }

      const result = await response.json()
      console.log("Analysis completed:", result)

      // Redirect to results page
      router.push(`/results/${jobId}`)
    } catch (err) {
      console.error("Analysis error:", err)
      setError("AI analysis failed")
    } finally {
      setIsAnalyzing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">Loading frames...</p>
        </div>
      </div>
    )
  }

  if (error || !jobStatus) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" />
              Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">{error || "Job not found"}</p>
            <Button onClick={() => router.push("/")} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Upload
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const frames = jobStatus.results?.frames || []

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold text-card-foreground">Extracted Frames</h1>
                <p className="text-sm text-muted-foreground">
                  Job ID: {jobId} • File: {jobStatus.filename}
                </p>
              </div>
            </div>
            <Button onClick={() => router.push("/")} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              New Analysis
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto space-y-8">
          {/* Frame Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ImageIcon className="h-5 w-5" />
                Frame Extraction Complete
              </CardTitle>
              <CardDescription>
                {frames.length} frames extracted every 2 seconds from your warehouse video
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <Badge variant="secondary" className="bg-chart-5 text-white">
                  <CheckCircle className="h-4 w-4 mr-2" />
                  {frames.length} Frames Ready
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Uploaded: {new Date(jobStatus.uploadedAt).toLocaleString()}
                </span>
              </div>
              
              <div className="flex gap-3">
                <Button 
                  onClick={handleStartAnalysis}
                  disabled={isAnalyzing}
                  className="bg-primary hover:bg-primary/90"
                >
                  {isAnalyzing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Analyzing with GPT-4o...
                    </>
                  ) : (
                    <>
                      <Brain className="h-4 w-4 mr-2" />
                      Start AI Safety Analysis
                    </>
                  )}
                </Button>
                
                <Button variant="outline" onClick={() => router.push(`/processing/${jobId}`)}>
                  Back to Processing
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Extracted Frames Gallery */}
          <Card>
            <CardHeader>
              <CardTitle>Extracted Frames Preview</CardTitle>
              <CardDescription>
                These frames will be analyzed for safety violations
              </CardDescription>
            </CardHeader>
            <CardContent>
              {frames.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {frames.map((frame, index) => (
                    <div key={index} className="space-y-3">
                      <div className="aspect-video relative rounded-lg overflow-hidden border">
                        <img
                          src={frame.imageUrl}
                          alt={`Frame at ${frame.time}`}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            // Fallback to placeholder if frame image fails to load
                            e.currentTarget.src = "/warehouse-hallway-with-potential-safety-issues.jpg"
                          }}
                        />
                        <div className="absolute top-2 left-2">
                          <Badge variant="secondary" className="bg-black/70 text-white">
                            {frame.time}
                          </Badge>
                        </div>
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-medium">Frame {index + 1}</p>
                        <p className="text-xs text-muted-foreground">Timestamp: {frame.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <XCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No frames available for analysis</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Analysis Info */}
          <Card>
            <CardHeader>
              <CardTitle>AI Safety Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <h4 className="font-semibold text-card-foreground">What We'll Check:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Incorrect parking blocking fire brigade access</li>
                    <li>• Waste materials obstructing emergency vehicles</li>
                    <li>• Objects in hallways that pose safety risks</li>
                  </ul>
                </div>
                <div className="space-y-2">
                  <h4 className="font-semibold text-card-foreground">Analysis Features:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• GPT-4o powered visual inspection</li>
                    <li>• Detailed explanations of findings</li>
                    <li>• Bounding boxes for detected violations</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
