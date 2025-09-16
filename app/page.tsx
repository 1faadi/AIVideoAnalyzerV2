"use client"

import type React from "react"

import { useState } from "react"
import { Upload, Shield, AlertTriangle, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { uploadAndStartProcessing } from "@/lib/job-manager"
import { useRouter } from "next/navigation"

export default function HomePage() {
  const router = useRouter()
  const [isDragging, setIsDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | { name: string; jobId: string } | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const videoFile = files.find((file) => file.type.startsWith("video/"))

    if (videoFile) {
      handleFileUpload(videoFile)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type.startsWith("video/")) {
      handleFileUpload(file)
    }
  }

  const handleFileUpload = async (file: File) => {
    setIsUploading(true)
    setUploadedFile(file)

    try {
      // Simulate upload progress
      for (let i = 0; i <= 100; i += 10) {
        setUploadProgress(i)
        await new Promise((resolve) => setTimeout(resolve, 200))
      }

      const jobId = await uploadAndStartProcessing(file)
      setIsUploading(false)

      // Store jobId for processing
      setUploadedFile({ ...file, jobId })
    } catch (error) {
      console.error("Upload failed:", error)
      setIsUploading(false)
      setUploadedFile(null)
      setUploadProgress(0)
    }
  }

  const handleStartAnalysis = async () => {
    if (!uploadedFile || typeof uploadedFile === "string") return

    setIsProcessing(true)
    const jobId = (uploadedFile as any).jobId

    try {
      // Navigate to processing page to start analysis
      router.push(`/processing/${jobId}`)
    } catch (error) {
      console.error("Navigation failed:", error)
      setIsProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold text-card-foreground">Warehouse Safety Inspector</h1>
              <p className="text-sm text-muted-foreground">Analysis of warehouse safety</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          {/* Welcome Section */}
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold text-foreground text-balance">
              Upload Warehouse Video for Safety Analysis
            </h2>
            <p className="text-lg text-muted-foreground text-pretty max-w-2xl mx-auto">
              Our AI system analyzes your warehouse footage to detect incorrect parking and waste materials that could
              obstruct emergency vehicles and fire brigade access.
            </p>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Safety Checks</CardTitle>
                <CheckCircle className="h-4 w-4 text-chart-5" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-card-foreground">2</div>
                <p className="text-xs text-muted-foreground">Parking & Waste Detection</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Analysis Speed</CardTitle>
                <AlertTriangle className="h-4 w-4 text-chart-4" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-card-foreground">~2min</div>
                <p className="text-xs text-muted-foreground">Per video processed</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
                <Shield className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-card-foreground">95%+</div>
                <p className="text-xs text-muted-foreground">Detection accuracy</p>
              </CardContent>
            </Card>
          </div>

          {/* Upload Section */}
          <Card className="border-2 border-dashed border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Warehouse Video
              </CardTitle>
              <CardDescription>
                Drag and drop your video file here, or click to browse. Supports MP4, AVI, MOV formats.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!isUploading && !uploadedFile ? (
                <div
                  className={`relative border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                    isDragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-lg font-medium text-foreground mb-2">Drop your warehouse video here</p>
                  <p className="text-sm text-muted-foreground mb-4">or click to select from your computer</p>
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleFileSelect}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Button variant="outline">Browse Files</Button>
                </div>
              ) : isUploading ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <Upload className="h-5 w-5 text-primary animate-pulse" />
                    <span className="font-medium">Uploading {uploadedFile?.name}...</span>
                  </div>
                  <Progress value={uploadProgress} className="w-full" />
                  <p className="text-sm text-muted-foreground">{uploadProgress}% complete</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 text-chart-5">
                    <CheckCircle className="h-5 w-5" />
                    <span className="font-medium">Upload Complete: {uploadedFile?.name}</span>
                  </div>
                  <div className="flex gap-3">
                    <Button
                      onClick={handleStartAnalysis}
                      disabled={isProcessing}
                      className="bg-primary hover:bg-primary/90"
                    >
                      {isProcessing ? "Starting Analysis..." : "Start Safety Analysis"}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setUploadedFile(null)
                        setUploadProgress(0)
                      }}
                      disabled={isProcessing}
                    >
                      Upload Another
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Instructions */}
          <Card>
            <CardHeader>
              <CardTitle>What We Analyze</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <h4 className="font-semibold text-card-foreground flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-chart-2" />
                    Incorrect Parking
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Vehicles parked in hallways or corridors that could block emergency vehicle access
                  </p>
                </div>
                <div className="space-y-2">
                  <h4 className="font-semibold text-card-foreground flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-chart-4" />
                    Waste Materials
                  </h4>
                  <p className="text-sm text-muted-foreground">
                    Bins, boxes, or materials placed in pathways that could obstruct emergency access
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
