function PageSection({ eyebrow, title, description, items = [] }) {
  return (
    <section className="space-y-6">
      <div className="space-y-3">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-amber-700">
          {eyebrow}
        </p>
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            {title}
          </h1>
          <p className="max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
            {description}
          </p>
        </div>
      </div>

      {items.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <article
              key={item.title}
              className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_22px_55px_-36px_rgba(15,23,42,0.28)]"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
                {item.kicker}
              </p>
              <h2 className="mt-3 text-lg font-semibold text-slate-950">
                {item.title}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {item.description}
              </p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}

export default PageSection
