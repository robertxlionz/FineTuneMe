import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({
    subsets: ["latin"],
    display: "swap",
})

export const metadata: Metadata = {
    title: "FineTuneMe - Synthetic Dataset Factory",
    description: "Generate high-quality training datasets from any document",
}

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode
}>) {
    return (
        <html lang="en">
            <body className={inter.className}>{children}</body>
        </html>
    )
}
