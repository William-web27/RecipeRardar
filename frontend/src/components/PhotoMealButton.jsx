import { useRef, useState } from "react";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Camera, Loader2 } from "lucide-react";
import { Button } from "./ui/button";

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const s = reader.result || "";
      const idx = s.indexOf(",");
      resolve(idx >= 0 ? s.slice(idx + 1) : s);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function PhotoMealButton({ onMealCreated }) {
  const inputRef = useRef(null);
  const [loading, setLoading] = useState(false);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!/image\/(jpeg|png|webp)/i.test(file.type)) {
      toast.error("Use a JPEG, PNG or WebP photo");
      return;
    }
    setLoading(true);
    try {
      const image_base64 = await fileToBase64(file);
      const { data } = await api.post("/meals/photo", {
        image_base64,
        mime_type: file.type || "image/jpeg",
      });
      toast.success("Meal analyzed", { description: data.summary });
      onMealCreated?.(data);
    } catch (err) {
      toast.error("Couldn't read that photo", { description: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={handleFile}
        className="hidden"
        data-testid="photo-file-input"
      />
      <Button
        type="button"
        variant="outline"
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        data-testid="photo-upload-btn"
        className="rounded-full border-emerald-300 text-emerald-700 hover:bg-emerald-50 hover:border-emerald-400 h-11 px-5 active:scale-95 transition-transform"
      >
        {loading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Reading photo…</> : <><Camera className="h-4 w-4 mr-2" /> Snap a photo</>}
      </Button>
    </>
  );
}
