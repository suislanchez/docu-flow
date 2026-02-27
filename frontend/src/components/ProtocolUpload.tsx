import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FileText, Loader2, AlertTriangle } from "lucide-react";
import { cn } from "../lib/utils";

interface ProtocolUploadProps {
  onUpload: (file: File) => void;
  uploading: boolean;
  filename: string | null;
  error: string | null;
}

export function ProtocolUpload({
  onUpload,
  uploading,
  filename,
  error,
}: ProtocolUploadProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) onUpload(accepted[0]);
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-slate-300">
        Protocol PDF
      </label>

      <div
        {...getRootProps()}
        className={cn(
          "group relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 cursor-pointer transition-all duration-200",
          isDragActive
            ? "border-brand-500 bg-brand-900/20"
            : "border-slate-600 hover:border-slate-500 bg-slate-800/40 hover:bg-slate-800/60",
          uploading && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <>
            <Loader2 className="w-10 h-10 text-brand-500 animate-spin" />
            <p className="text-sm text-slate-300 font-medium">Uploading…</p>
          </>
        ) : filename ? (
          <>
            <FileText className="w-10 h-10 text-brand-500" />
            <div className="text-center">
              <p className="text-sm font-medium text-slate-200">{filename}</p>
              <p className="text-xs text-slate-400 mt-1">Drop a new PDF to replace</p>
            </div>
          </>
        ) : (
          <>
            <UploadCloud
              className={cn(
                "w-10 h-10 transition-colors",
                isDragActive ? "text-brand-400" : "text-slate-500 group-hover:text-slate-400"
              )}
            />
            <div className="text-center">
              <p className="text-sm font-medium text-slate-300">
                {isDragActive ? "Drop it here" : "Drop a protocol PDF"}
              </p>
              <p className="text-xs text-slate-500 mt-1">or click to browse</p>
            </div>
          </>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-red-900/30 border border-red-500/30 px-3 py-2 text-sm text-red-300">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
