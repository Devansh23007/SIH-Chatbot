import { BookOpen, Briefcase, Lightbulb, ListOrdered, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import type {
  CareerRecommendation, CourseRecommendation, JobRole, LearningPath, RecommendationBlock, SkillGap,
} from '../../types/chatbot';
import { safeUrl } from '../../utils/chatbotUtils';

function Card({ icon: Icon, kind, title, children, url }: { icon: LucideIcon; kind: string; title: string; children?: ReactNode; url?: string }) {
  const href = safeUrl(url);
  return (
    <article className="cb-card">
      <header className="cb-card__head">
        <span className="cb-card__icon" aria-hidden="true"><Icon size={16} /></span>
        <div>
          <p className="cb-card__kind">{kind}</p>
          <h4 className="cb-card__title">{title}</h4>
        </div>
      </header>
      {children}
      {href && <a className="cb-card__link" href={href} target="_blank" rel="noopener noreferrer">View details</a>}
    </article>
  );
}

const Chips = ({ items, missing, label }: { items?: string[]; missing?: boolean; label: string }) =>
  items?.length ? (
    <div className="cb-card__group">
      <span className="cb-card__label">{label}</span>
      <ul className="cb-chips">{items.map((s) => <li key={s} className={missing ? 'cb-chip cb-chip--missing' : 'cb-chip'}>{s}</li>)}</ul>
    </div>
  ) : null;

export function CareerRecommendationCard({ data }: { data: CareerRecommendation }) {
  return (
    <Card icon={Briefcase} kind="Career match" title={data.title} url={data.url}>
      {data.matchPercentage !== undefined && (
        <div className="cb-match">
          <div className="cb-match__bar" role="progressbar" aria-label={`Profile match for ${data.title}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={data.matchPercentage}>
            <span style={{ width: `${Math.min(100, Math.max(0, data.matchPercentage))}%` }} />
          </div>
          <span className="cb-match__value">{data.matchPercentage}% match</span>
        </div>
      )}
      {data.description && <p className="cb-card__text">{data.description}</p>}
      <Chips items={data.requiredSkills} label="Required skills" />
      <Chips items={data.missingSkills} missing label="To develop" />
    </Card>
  );
}

export function CourseRecommendationCard({ data }: { data: CourseRecommendation }) {
  const meta = [data.provider, data.level, data.duration].filter(Boolean).join(' • ');
  return (
    <Card icon={BookOpen} kind="Course" title={data.title} url={data.url}>
      {meta && <p className="cb-card__meta">{meta}</p>}
      {data.description && <p className="cb-card__text">{data.description}</p>}
      <Chips items={data.skills} label="You will build" />
    </Card>
  );
}

export function SkillGapCard({ data }: { data: SkillGap }) {
  return (
    <Card icon={Lightbulb} kind="Skill gap" title={data.targetRole ? `Gaps for ${data.targetRole}` : 'Your skill gaps'}>
      <Chips items={data.missingSkills} missing label="Missing" />
      <Chips items={data.partialSkills} label="Needs strengthening" />
    </Card>
  );
}

export function LearningPathCard({ data }: { data: LearningPath }) {
  return (
    <Card icon={ListOrdered} kind="Learning path" title={data.title}>
      <ol className="cb-steps">
        {data.steps.map((s, i) => (
          <li key={i}>
            <strong>{s.title}</strong>
            {s.duration && <span className="cb-card__meta"> {s.duration}</span>}
            {s.description && <p className="cb-card__text">{s.description}</p>}
          </li>
        ))}
      </ol>
    </Card>
  );
}

export function JobRoleCard({ data }: { data: JobRole }) {
  const meta = [data.company, data.location].filter(Boolean).join(' • ');
  return (
    <Card icon={Briefcase} kind="Job role" title={data.title} url={data.url}>
      {meta && <p className="cb-card__meta">{meta}</p>}
      {data.description && <p className="cb-card__text">{data.description}</p>}
      <Chips items={data.skills} label="Skills" />
    </Card>
  );
}

/** Add a new `type` here when the backend introduces another structured block. */
export function RecommendationBlockView({ block }: { block: RecommendationBlock }) {
  switch (block.type) {
    case 'career_recommendation': return <CareerRecommendationCard data={block} />;
    case 'course_recommendation': return <CourseRecommendationCard data={block} />;
    case 'skill_gap': return <SkillGapCard data={block} />;
    case 'learning_path': return <LearningPathCard data={block} />;
    case 'job_role': return <JobRoleCard data={block} />;
    default: return null; // unknown block types are ignored, never crash the chat
  }
}
