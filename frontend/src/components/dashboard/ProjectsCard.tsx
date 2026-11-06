import React from 'react';
import { FolderGit2, Cpu } from 'lucide-react';
import { ProjectItem } from '../../types/api';

interface ProjectsCardProps {
  projects: ProjectItem[];
}

export const ProjectsCard: React.FC<ProjectsCardProps> = ({ projects }) => {
  if (!projects || projects.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 text-center text-slate-500">
        <FolderGit2 className="w-8 h-8 mx-auto text-slate-300 mb-2" />
        <p className="text-sm">No projects extracted from resume.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-slate-800">Verified Projects</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Key engineering projects evaluated for domain relevance in SBERT career matching.
          </p>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200/80">
          {projects.length} Projects Analyzed
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((proj, idx) => (
          <div
            key={idx}
            className="flex flex-col justify-between p-4 rounded-xl border border-slate-200/90 bg-slate-50/50 hover:bg-slate-50 hover:border-indigo-300 transition-all duration-200 shadow-xs"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-indigo-100/70 text-indigo-700">
                    <FolderGit2 className="w-4 h-4" />
                  </div>
                  <h4 className="font-bold text-sm text-slate-800 leading-snug line-clamp-1">
                    {proj.name || `Project #${idx + 1}`}
                  </h4>
                </div>
              </div>

              {proj.description && (
                <p className="text-xs text-slate-600 leading-relaxed mb-3 line-clamp-4">
                  {proj.description}
                </p>
              )}
            </div>

            {proj.technologies && proj.technologies.length > 0 && (
              <div className="pt-3 border-t border-slate-200/70">
                <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-500 mb-1.5">
                  <Cpu className="w-3 h-3 text-indigo-500" />
                  <span>Stack</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {proj.technologies.map((tech) => (
                    <span
                      key={tech}
                      className="px-2 py-0.5 text-[10px] font-medium bg-white text-slate-700 border border-slate-200 rounded-md shadow-2xs"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
