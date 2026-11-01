import { useEffect, useState } from 'react';

import type { ApiClient, Group } from '../api/client';

export interface Groups {
  groups: Group[] | null;
  failed: boolean;
}

/** Loads the list of CelesTrak groups once. */
export function useGroups(api: ApiClient): Groups {
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    api
      .listGroups(controller.signal)
      .then(setGroups)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
    };
  }, [api]);

  return { groups, failed };
}
