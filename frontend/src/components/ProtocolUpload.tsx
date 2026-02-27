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
      <div
        {...getRootProps()}
        className={cn(
          "group relative flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 cursor-pointer transition-all duration-200",
          isDragActive
            ? "border-blue-400 bg-blue-50"
            : "border-gray-300 hover:border-gray-400 bg-gray-50 hover:bg-gray-100",
          uploading && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <>
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
            <p className="text-sm text-gray-600 font-medium">Uploading...</p>
          </>
        ) : filename ? (
          <>
            <FileText className="w-10 h-10 text-blue-500" />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-800">{filename}</p>
              <p className="text-xs text-gray-400 mt-1">Drop a new PDF to replace</p>
            </div>
          </>
        ) : (
          <>
            <UploadCloud
              className={cn(
                "w-10 h-10 transition-colors",
                isDragActive ? "text-blue-500" : "text-gray-400 group-hover:text-gray-500"
              )}
            />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-600">
                {isDragActive ? "Drop it here" : "Drop a protocol PDF"}
              </p>
              <p className="text-xs text-gray-400 mt-1">or click to browse</p>
            </div>
          </>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
