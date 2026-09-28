import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import Cropper, { type Area } from 'react-easy-crop';
import { useEscape } from '@/hooks/useScrollLock';

const MAX_SIDE = 2400;

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

/** Crops (and rotates) `src` to `area` and returns a JPEG data URI. */
export async function cropToDataUrl(src: string, area: Area, rotation = 0): Promise<string> {
  const img = await loadImage(src);
  const rad = (rotation * Math.PI) / 180;
  const sin = Math.abs(Math.sin(rad));
  const cos = Math.abs(Math.cos(rad));
  const bw = img.width * cos + img.height * sin;
  const bh = img.width * sin + img.height * cos;

  // Draw the rotated image on a bounding canvas, then cut the area out of it.
  const rotated = document.createElement('canvas');
  rotated.width = bw;
  rotated.height = bh;
  const rctx = rotated.getContext('2d')!;
  rctx.translate(bw / 2, bh / 2);
  rctx.rotate(rad);
  rctx.drawImage(img, -img.width / 2, -img.height / 2);

  const scale = Math.min(1, MAX_SIDE / Math.max(area.width, area.height));
  const out = document.createElement('canvas');
  out.width = Math.round(area.width * scale);
  out.height = Math.round(area.height * scale);
  const ctx = out.getContext('2d')!;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(rotated, area.x, area.y, area.width, area.height, 0, 0, out.width, out.height);
  return out.toDataURL('image/jpeg', 0.92);
}

export function readAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

type ModalProps = {
  src: string | null;
  /** Width / height; omitted = the photo's own proportions. */
  aspect?: number;
  onApply: (dataUrl: string) => void;
  onClose: () => void;
};

/** "Редагування фото": crop, rotate and zoom before upload (react-easy-crop). */
export function ImageCropModal({ src, aspect, onApply, onClose }: ModalProps) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [area, setArea] = useState<Area | null>(null);
  const [natural, setNatural] = useState<number | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  useEscape(!!src, onClose);

  const reset = useCallback(() => {
    setCrop({ x: 0, y: 0 });
    setZoom(1);
    setRotation(0);
  }, []);

  useEffect(() => {
    reset();
    setNatural(undefined);
    if (src && !aspect) loadImage(src).then((img) => setNatural(img.width / img.height)).catch(() => setNatural(1));
  }, [src, aspect, reset]);

  if (!src) return null;
  const ratio = aspect ?? natural;

  const apply = async () => {
    if (!area) return;
    setBusy(true);
    try {
      onApply(await cropToDataUrl(src, area, rotation));
      onClose();
    } finally {
      setBusy(false);
    }
  };

  return createPortal(
    <div id="imgCropModal" className="open" role="dialog" aria-modal="true" aria-label="Редагування фото">
      <div className="icm-backdrop" onClick={onClose} />
      <div className="icm-dialog">
        <div className="icm-header">
          <span className="icm-title">Редагування фото</span>
          <button className="icm-close" type="button" onClick={onClose} aria-label="Закрити">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div className="icm-body">
          {ratio && (
            <Cropper
              image={src}
              crop={crop}
              zoom={zoom}
              rotation={rotation}
              aspect={ratio}
              minZoom={0.5}
              maxZoom={5}
              restrictPosition={false}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={(_, px) => setArea(px)}
            />
          )}
        </div>
        <div className="icm-toolbar">
          <button type="button" onClick={() => setRotation((r) => r - 90)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /></svg>
            Вліво
          </button>
          <button type="button" onClick={() => setRotation((r) => r + 90)}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 12a9 9 0 1 1-9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /></svg>
            Вправо
          </button>
          <button type="button" id="icmZoomIn" aria-label="Збільшити" onClick={() => setZoom((z) => Math.min(5, z + 0.1))}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="11" y1="8" x2="11" y2="14" /><line x1="8" y1="11" x2="14" y2="11" /></svg>
          </button>
          <button type="button" id="icmZoomOut" aria-label="Зменшити" onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="8" y1="11" x2="14" y2="11" /></svg>
          </button>
          <button type="button" onClick={reset}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 1 0 .49-4.47" /></svg>
            Скинути
          </button>
          <div className="icm-toolbar-sep" />
          <span className="icm-hint">Тягни фото · Scroll = зум</span>
        </div>
        <div className="icm-footer">
          <button type="button" className="icm-btn icm-btn--sec" onClick={onClose}>
            Скасувати
          </button>
          <button type="button" className="icm-btn icm-btn--pri" disabled={busy || !area} onClick={apply}>
            Застосувати
          </button>
        </div>
      </div>
    </div>,
    document.querySelector('.pg-admin') ?? document.body,
  );
}

/**
 * State for one photo input: the picked file, its data URI (for preview
 * and the cropper) and the cropped result. Upload sends `b64` when the
 * admin cropped, otherwise the raw file.
 */
export function useImagePick() {
  const [file, setFile] = useState<File | null>(null);
  const [original, setOriginal] = useState<string | null>(null);
  const [b64, setB64] = useState<string | null>(null);
  const [cropping, setCropping] = useState(false);

  const pick = async (f: File | undefined | null) => {
    if (!f) return;
    setFile(f);
    setB64(null);
    setOriginal(await readAsDataUrl(f));
  };
  const reset = useCallback(() => {
    setFile(null);
    setOriginal(null);
    setB64(null);
    setCropping(false);
  }, []);

  return {
    file,
    original,
    b64,
    /** What to show: the cropped version, else the picked original. */
    preview: b64 ?? original,
    picked: !!file,
    pick,
    reset,
    cropping,
    openCropper: () => original && setCropping(true),
    closeCropper: () => setCropping(false),
    setB64,
    /** Adds `image_b64` or the raw file to a FormData under the given names. */
    append(fd: FormData, fileField: string, b64Field: string) {
      if (b64) fd.append(b64Field, b64);
      else if (file) fd.append(fileField, file);
    },
  };
}

export type ImagePick = ReturnType<typeof useImagePick>;

/** Cropper wiring for a `useImagePick` state. */
export function PickCropper({ pick, aspect, onApplied }: { pick: ImagePick; aspect?: number; onApplied?: (b64: string) => void }) {
  return (
    <ImageCropModal
      src={pick.cropping ? pick.original : null}
      aspect={aspect}
      onClose={pick.closeCropper}
      onApply={(b64) => {
        pick.setB64(b64);
        onApplied?.(b64);
      }}
    />
  );
}

const EditIcon = (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
);

/**
 * The dashed ".upload-zone" drop area: an invisible file input over a
 * placeholder, then a preview with a "Редагувати" (crop) button.
 */
export function UploadZone({
  pick,
  aspect,
  accept = 'image/jpeg,image/png,image/webp',
  placeholder,
  className = 'upload-zone',
  onApplied,
}: {
  pick: ImagePick;
  aspect?: number;
  accept?: string;
  placeholder: ReactNode;
  className?: string;
  onApplied?: (b64: string) => void;
}) {
  return (
    <>
      <div className={className}>
        <input type="file" accept={accept} onChange={(e) => pick.pick(e.target.files?.[0])} onClick={(e) => ((e.target as HTMLInputElement).value = '')} />
        {pick.preview ? (
          <div className="upload-preview" style={{ display: 'block' }}>
            <img src={pick.preview} alt="" style={{ maxHeight: 110, borderRadius: 8, objectFit: 'cover', display: 'block' }} />
            <button
              type="button"
              className="upload-recrop"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                pick.openCropper();
              }}
            >
              {EditIcon}
              {pick.b64 ? 'Переобрати' : 'Редагувати'}
            </button>
          </div>
        ) : (
          <div className="upload-zone__placeholder">{placeholder}</div>
        )}
      </div>
      <PickCropper pick={pick} aspect={aspect} onApplied={onApplied} />
    </>
  );
}

export const UploadIcon = (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#c9b49a" strokeWidth="1.5" strokeLinecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
);
