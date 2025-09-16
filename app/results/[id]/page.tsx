"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Shield, AlertTriangle, CheckCircle, XCircle, ArrowLeft, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { type JobStatus } from "@/lib/job-manager"
import { AnnotatedImage } from "@/components/annotated-image"

export default function ResultsPage() {
  const params = useParams()
  const router = useRouter()
  const jobId = params.id as string

  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}`)
        if (!response.ok) {
          throw new Error(`Failed to fetch job: ${response.statusText}`)
        }
        
        const status = await response.json()
        setJobStatus(status)
        
        // If job is still processing, redirect to processing page
        if (status.status === 'processing' || status.status === 'pending') {
          router.push(`/processing/${jobId}`)
          return
        }
        
        // If frames are extracted but no AI analysis done yet, redirect to frames page
        if (status.results?.frames && 
            status.results.explanation.includes("Ready for AI analysis")) {
          router.push(`/frames/${jobId}`)
          return
        }
        
      } catch (err) {
        setError("Failed to load results")
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    if (jobId) {
      fetchResults()
    }
  }, [jobId, router])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">Loading results...</p>
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
            <p className="text-muted-foreground mb-4">{error || "Results not found"}</p>
            <Button onClick={() => router.push("/")} variant="outline">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Upload
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const results = jobStatus.results

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold text-card-foreground">Safety Analysis Results</h1>
                <p className="text-sm text-muted-foreground">Job ID: {jobId}</p>
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
          {/* File Info */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Summary</CardTitle>
              <CardDescription>
                File: {jobStatus.filename} • Uploaded: {new Date(jobStatus.uploadedAt).toLocaleString()}
              </CardDescription>
            </CardHeader>
          </Card>

          {results ? (
            <>
              {/* Priority Actions Summary */}
              {(() => {
                const allHazards = results.frames?.flatMap(frame => frame.boundingBoxes || []) || []
                const criticalHazards = allHazards.filter(h => h.severity === 'critical')
                const urgentActions = allHazards.filter(h => h.immediate_action)
                const totalHazards = allHazards.length

                return totalHazards > 0 ? (
                  <Card className="border-2 border-orange-200 bg-orange-50">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-orange-800">
                        <AlertTriangle className="h-5 w-5" />
                        Priority Safety Actions Required
                      </CardTitle>
                      <CardDescription className="text-orange-700">
                        Immediate attention needed for detected safety hazards
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center p-3 bg-red-100 rounded-lg">
                          <div className="text-2xl font-bold text-red-800">{criticalHazards.length}</div>
                          <div className="text-sm text-red-600">Critical Hazards</div>
                        </div>
                        <div className="text-center p-3 bg-yellow-100 rounded-lg">
                          <div className="text-2xl font-bold text-yellow-800">{urgentActions.length}</div>
                          <div className="text-sm text-yellow-600">Urgent Actions</div>
                        </div>
                        <div className="text-center p-3 bg-blue-100 rounded-lg">
                          <div className="text-2xl font-bold text-blue-800">{totalHazards}</div>
                          <div className="text-sm text-blue-600">Total Issues</div>
                        </div>
                      </div>
                      
                      {urgentActions.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="font-semibold text-orange-800">Immediate Actions Required:</h4>
                          {urgentActions.slice(0, 3).map((hazard, index) => (
                            <div key={index} className="flex items-center gap-2 p-2 bg-white rounded border-l-4 border-red-500">
                              <AlertTriangle className="h-4 w-4 text-red-500" />
                              <span className="text-sm">
                                <strong>{hazard.label.split(" - ")[0]}:</strong> {hazard.mitigation_summary}
                              </span>
                            </div>
                          ))}
                          {urgentActions.length > 3 && (
                            <p className="text-sm text-orange-600">
                              + {urgentActions.length - 3} more urgent actions (see detailed analysis below)
                            </p>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ) : null
              })()}

              {/* Safety Verdicts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="border-2">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <AlertTriangle className="h-5 w-5" />
                      Incorrect Parking
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-3">
                      {results.incorrectParking ? (
                        <>
                          <Badge variant="destructive" className="text-base px-4 py-2">
                            <XCircle className="h-4 w-4 mr-2" />
                            VIOLATION DETECTED
                          </Badge>
                        </>
                      ) : (
                        <>
                          <Badge variant="secondary" className="text-base px-4 py-2 bg-chart-5 text-white">
                            <CheckCircle className="h-4 w-4 mr-2" />
                            NO VIOLATIONS
                          </Badge>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-2">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <AlertTriangle className="h-5 w-5" />
                      Waste Materials
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-3">
                      {results.wasteMaterial ? (
                        <>
                          <Badge variant="destructive" className="text-base px-4 py-2">
                            <XCircle className="h-4 w-4 mr-2" />
                            VIOLATION DETECTED
                          </Badge>
                        </>
                      ) : (
                        <>
                          <Badge variant="secondary" className="text-base px-4 py-2 bg-chart-5 text-white">
                            <CheckCircle className="h-4 w-4 mr-2" />
                            NO VIOLATIONS
                          </Badge>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Detailed Explanation */}
              <Card>
                <CardHeader>
                  <CardTitle>Detailed Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-foreground leading-relaxed text-pretty">{results.explanation}</p>
                </CardContent>
              </Card>

              {/* Detailed Frame Analysis */}
              {results.frameDetails && results.frameDetails.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      Detailed Frame-by-Frame Safety Analysis
                      <Badge variant="outline">{results.frameDetails.length} frame(s)</Badge>
                    </CardTitle>
                    <CardDescription>Comprehensive safety assessment for each analyzed frame</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-8">
                      {results.frameDetails.map((frameDetail: any, index: number) => (
                        <div key={index} className="border rounded-lg p-6 space-y-6">
                          {/* Frame Header */}
                          <div className="flex items-center justify-between border-b pb-4">
                            <div>
                              <h3 className="text-lg font-semibold text-card-foreground">
                                Frame {frameDetail.frameIndex + 1}
                              </h3>
                              <p className="text-sm text-muted-foreground">Timestamp: {frameDetail.timestamp}</p>
                            </div>
                            {frameDetail.safetyIssues && frameDetail.safetyIssues.length > 0 && (
                              <Badge variant="destructive">
                                {frameDetail.safetyIssues.length} Issue(s) Found
                              </Badge>
                            )}
                          </div>

                          {/* Frame Image with Annotations */}
                          {results.frames && results.frames[index] && (
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <h4 className="font-semibold text-card-foreground">Frame Analysis</h4>
                                {results.frames[index].boundingBoxes && results.frames[index].boundingBoxes.length > 0 && (
                                  <Badge variant="outline">
                                    {results.frames[index].boundingBoxes.length} annotation(s)
                                  </Badge>
                                )}
                              </div>
                              <AnnotatedImage
                                src={results.frames[index].imageUrl}
                                alt={`Frame at ${frameDetail.timestamp}`}
                                boundingBoxes={results.frames[index].boundingBoxes || []}
                              />
                              {results.frames[index].boundingBoxes && results.frames[index].boundingBoxes.length > 0 && (
                                <div className="space-y-3">
                                  <h5 className="font-medium text-foreground">Detected Safety Issues:</h5>
                                  {results.frames[index].boundingBoxes.map((box: any, boxIndex: number) => (
                                    <div key={boxIndex} className="border rounded-lg p-3 space-y-2">
                                      <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                          <div className={`w-3 h-3 rounded-sm ${
                                            box.severity === 'critical' ? 'bg-red-500' :
                                            box.severity === 'high' ? 'bg-orange-500' :
                                            box.severity === 'medium' ? 'bg-yellow-500' :
                                            'bg-green-500'
                                          }`}></div>
                                          <span className="font-medium capitalize">{box.label.split(" - ")[0]}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                          <Badge variant={
                                            box.severity === 'critical' ? 'destructive' :
                                            box.severity === 'high' ? 'secondary' :
                                            'outline'
                                          }>
                                            {box.severity?.toUpperCase() || 'UNKNOWN'}
                                          </Badge>
                                          {box.immediate_action && (
                                            <Badge variant="default" className="bg-yellow-500 text-black">
                                              URGENT
                                            </Badge>
                                          )}
                                        </div>
                                      </div>
                                      
                                      {box.reason && (
                                        <p className="text-sm text-muted-foreground">
                                          <strong>Issue:</strong> {box.reason}
                                        </p>
                                      )}
                                      
                                      {box.mitigation_summary && (
                                        <p className="text-sm text-muted-foreground">
                                          <strong>Action Required:</strong> {box.mitigation_summary}
                                        </p>
                                      )}
                                      
                                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                        {box.confidence && (
                                          <span>Confidence: {(box.confidence * 100).toFixed(1)}%</span>
                                        )}
                                        {box.source && (
                                          <span>Source: {box.source.replace('_', ' ')}</span>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Detailed Observations */}
                          <div className="space-y-4">
                            <div>
                              <h4 className="font-semibold text-card-foreground mb-2">Detailed Observations</h4>
                              <p className="text-foreground leading-relaxed bg-muted p-4 rounded-lg">
                                {frameDetail.detailedObservations}
                              </p>
                            </div>

                            {/* Safety Issues */}
                            {frameDetail.safetyIssues && frameDetail.safetyIssues.length > 0 && (
                              <div>
                                <h4 className="font-semibold text-card-foreground mb-3">Safety Issues Identified</h4>
                                <div className="space-y-3">
                                  {frameDetail.safetyIssues.map((issue: any, issueIndex: number) => (
                                    <div key={issueIndex} className="border-l-4 border-destructive bg-destructive/5 p-4 rounded-r-lg">
                                      <div className="flex items-center gap-2 mb-2">
                                        <Badge variant={
                                          issue.severity === 'critical' ? 'destructive' :
                                          issue.severity === 'high' ? 'destructive' :
                                          issue.severity === 'medium' ? 'default' : 'secondary'
                                        }>
                                          {issue.severity?.toUpperCase()} - {issue.type?.toUpperCase()}
                                        </Badge>
                                      </div>
                                      <p className="font-medium text-foreground mb-1">{issue.description}</p>
                                      <p className="text-sm text-muted-foreground mb-1">
                                        <strong>Location:</strong> {issue.location}
                                      </p>
                                      <p className="text-sm text-muted-foreground">
                                        <strong>Emergency Impact:</strong> {issue.impact}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Pathway & Emergency Access */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="bg-muted p-4 rounded-lg">
                                <h5 className="font-semibold text-card-foreground mb-2">Pathway Clearance</h5>
                                <p className="text-sm text-foreground">{frameDetail.pathwayClearance}</p>
                              </div>
                              <div className="bg-muted p-4 rounded-lg">
                                <h5 className="font-semibold text-card-foreground mb-2">Emergency Access</h5>
                                <p className="text-sm text-foreground">{frameDetail.emergencyAccess}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Legacy Annotated Images (if no detailed analysis available) */}
              {(!results.frameDetails || results.frameDetails.length === 0) && results.frames && results.frames.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      Detected Violations
                      <Badge variant="outline">{results.frames.length} frame(s)</Badge>
                    </CardTitle>
                    <CardDescription>Images showing detected safety violations with highlighted areas</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {results.frames.map((frame, index) => (
                        <div key={index} className="space-y-3">
                          <div className="flex items-center justify-between">
                            <h4 className="font-semibold text-card-foreground">Timestamp: {frame.time}</h4>
                            <Badge variant="outline">{frame.boundingBoxes.length} violation(s)</Badge>
                          </div>
                          <AnnotatedImage
                            src={frame.imageUrl}
                            alt={`Frame at ${frame.time}`}
                            boundingBoxes={frame.boundingBoxes}
                          />
                          <div className="space-y-2">
                            {frame.boundingBoxes.map((box, boxIndex) => (
                              <div key={boxIndex} className="border rounded-md p-2 space-y-1">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <div className={`w-2 h-2 rounded-sm ${
                                      box.severity === 'critical' ? 'bg-red-500' :
                                      box.severity === 'high' ? 'bg-orange-500' :
                                      box.severity === 'medium' ? 'bg-yellow-500' :
                                      'bg-green-500'
                                    }`}></div>
                                    <span className="text-sm font-medium capitalize">{box.label.split(" - ")[0]}</span>
                                  </div>
                                  <Badge variant={
                                    box.severity === 'critical' ? 'destructive' :
                                    box.severity === 'high' ? 'secondary' :
                                    'outline'
                                  } className="text-xs">
                                    {box.severity?.toUpperCase() || 'ISSUE'}
                                  </Badge>
                                </div>
                                {box.reason && (
                                  <p className="text-xs text-muted-foreground">{box.reason}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Actions */}
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-wrap gap-3">
                    <Button onClick={() => router.push("/")} className="bg-primary hover:bg-primary/90">
                      Analyze Another Video
                    </Button>
                    <Button variant="outline">
                      <Download className="h-4 w-4 mr-2" />
                      Download Report
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="pt-6 text-center">
                <p className="text-muted-foreground">No analysis results available for this job.</p>
                <Button onClick={() => router.push("/")} className="mt-4" variant="outline">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Upload
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  )
}
