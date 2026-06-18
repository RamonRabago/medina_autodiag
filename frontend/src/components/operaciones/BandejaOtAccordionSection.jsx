import BandejaOtSection from './BandejaOtSection'
import DisclosurePanel, { DisclosureChevron } from '../ui/DisclosurePanel'

/**
 * Wrapper accordion para bandejas OT (UX-1A).
 * BandejaOtSection permanece intacto; título duplicado oculto visualmente.
 */
export default function BandejaOtAccordionSection({
  sectionId,
  titulo,
  total = 0,
  expanded,
  onToggle,
  ...bandejaProps
}) {
  return (
    <DisclosurePanel
      id={sectionId}
      expanded={expanded}
      onToggle={onToggle}
      className="mb-6"
      trigger={
        <>
          <span className="text-lg font-semibold text-slate-800">{titulo}</span>
          <span className="text-sm font-normal text-slate-500">({total})</span>
          <DisclosureChevron expanded={expanded} />
        </>
      }
    >
      {expanded && (
        <div className="px-4 pb-4 [&_section>h2:first-of-type]:sr-only [&_section]:mb-0">
          <BandejaOtSection titulo={titulo} total={total} {...bandejaProps} />
        </div>
      )}
    </DisclosurePanel>
  )
}
