import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/server/guard";
import { correlationId } from "@/lib/api/fetcher";
import {
  fetchUpstream,
  isPublicNestOnlyMode,
  localOnlyFeatureDisabledResponse,
  safeMustEnv,
} from "@/lib/server/upstream";

export async function GET(req: NextRequest) {
  const auth = await requireAdmin();
  if (!auth.ok) return auth.response;
  if (isPublicNestOnlyMode()) return localOnlyFeatureDisabledResponse("news");

  const limit = req.nextUrl.searchParams.get("limit") || "20";
  const fastapiEnv = safeMustEnv("FASTAPI_BASE_URL");
  if (!fastapiEnv.ok) return fastapiEnv.response;
  const apiKeyEnv = safeMustEnv("FASTAPI_INTERNAL_API_KEY");
  if (!apiKeyEnv.ok) return apiKeyEnv.response;
  const fastapi = fastapiEnv.value.replace(/\/$/, "");
  const apiKey = apiKeyEnv.value;
  const url = `${fastapi}/api/v1/news?limit=${encodeURIComponent(limit)}`;

  return fetchUpstream(
    url,
    {
      headers: {
        "x-api-key": apiKey,
        "x-correlation-id": correlationId("news"),
      },
      next: { revalidate: 20 },
    },
    "fastapi",
  );
}

