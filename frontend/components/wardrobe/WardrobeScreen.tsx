"use client";

import { useRef, useState } from "react";
import { GuideMascot } from "@/components/guide/GuideMascot";
import { useGuide } from "@/components/guide/GuideProvider";
import { usePreferences } from "@/components/layout/PreferencesProvider";
import { Button } from "@/components/ui/Button";
import { DemoDataPlate } from "@/components/ui/DemoDataPlate";
import type { Outfit } from "@/lib/types";
import { exportMascotPng } from "./exportMascotPng";

type Category = keyof Outfit;

export function WardrobeScreen() {
  const { t } = usePreferences();
  const g = t.guide;
  const guide = useGuide();
  const [category, setCategory] = useState<Category>("top");
  const stage = useRef<HTMLDivElement>(null);

  const categories: { key: Category; label: string; options: { value: string; label: string }[] }[] = [
    { key: "top", label: g.catTop, options: [{ value: "hoodie", label: g.hoodie }, { value: "tshirt", label: g.tshirt }, { value: "varsity", label: g.varsity }] },
    { key: "head", label: g.catHead, options: [{ value: "cap", label: g.cap }, { value: "none", label: g.none }] },
    { key: "accessory", label: g.catAcc, options: [{ value: "backpack", label: g.backpack }, { value: "scarf", label: g.scarf }, { value: "none", label: g.none }] },
  ];
  const active = categories.find((c) => c.key === category) ?? categories[0];
  const { brand } = guide;

  const savePng = () => {
    const svg = stage.current?.querySelector("svg");
    if (svg) exportMascotPng(svg, brand, "kampi-ku.png");
  };

  return (
    <div className="mx-auto max-w-[1000px] px-[22px] pb-[90px] pt-9">
      <DemoDataPlate className="mb-[22px]" />
      <h2 className="mb-1.5 text-[28px] font-semibold tracking-[-0.02em]">{g.wardrobeTitle}</h2>
      <div className="mb-[26px] flex flex-wrap items-center gap-1.5 text-xs text-ink-3">
        <span>{g.wardrobeNote}</span>
        {brand.hasColors && brand.sourceUrl ? (
          <a href={brand.sourceUrl} target="_blank" rel="noreferrer">
            {g.colorsFrom}: {brand.source === "wikidata" ? "Wikidata" : g.officialSite}
          </a>
        ) : (
          <span>{g.colorsNotFound}</span>
        )}
      </div>

      <div className="flex flex-wrap items-start gap-[26px]">
        <div className="flex-[0_0_150px]">
          {categories.map((c) => (
            <button
              key={c.key}
              onClick={() => setCategory(c.key)}
              className={`flex w-full border-x-0 border-b border-t-0 border-line bg-transparent py-[9px] text-left text-[13.5px] ${
                category === c.key ? "font-medium text-ink" : "text-ink-3"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="flex min-w-0 flex-[1_1_300px] flex-col gap-4">
          <div
            ref={stage}
            className="flex justify-center rounded-[14px] pt-[22px]"
            style={{ background: `linear-gradient(170deg, ${brand.primary} 0%, ${brand.secondary} 100%)` }}
          >
            <GuideMascot height={300} />
          </div>
          <div className="flex flex-wrap gap-2.5">
            {active.options.map((o) => {
              const on = guide.outfit[active.key] === o.value;
              return (
                <button
                  key={o.value}
                  onClick={() => guide.setOutfitPart(active.key, o.value as Outfit[typeof active.key])}
                  className={`rounded-full border-none px-[18px] py-[11px] text-[13px] ${on ? "bg-accent-soft text-accent" : "bg-surface-2 text-ink-2"}`}
                >
                  {o.label}
                </button>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={guide.randomOutfit} className="px-[18px] py-[11px] text-[13px] font-normal">
              {g.random}
            </Button>
            <Button variant="secondary" onClick={savePng} className="px-[18px] py-[11px] text-[13px]">
              {g.savePng}
            </Button>
          </div>
          <div className="max-w-[52ch] text-[11.5px] leading-normal text-ink-3">{g.demoNote}</div>
        </div>
      </div>
    </div>
  );
}
