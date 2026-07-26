/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { useCallback, useMemo, useState } from 'react';
import rison from 'rison';
import { t, SupersetClient } from '@superset-ui/core';
import { useListViewResource } from 'src/views/CRUD/hooks';
import withToasts from 'src/components/MessageToasts/withToasts';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import {
  FormModal,
  FormItem,
  AsyncSelect,
  Icons,
} from '@superset-ui/core/components';
import { ModalTitleWithIcon } from 'src/components/ModalTitleWithIcon';
import {
  ListView,
  ListViewActionsBar,
  type ListViewActionProps,
  type ListViewFilters,
} from 'src/components';

const RESOURCE = 'guest_rls_exempt_dataset';

type ExemptObject = {
  id: number;
  dataset?: { id: number; table_name: string };
};

interface Props {
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

interface ExemptModalProps {
  show: boolean;
  onHide: () => void;
  onSave: () => void;
  addDangerToast: (msg: string) => void;
  addSuccessToast: (msg: string) => void;
}

// Loader for the dataset picker — searches all datasets via the related endpoint.
const loadDatasetOptions = (input = '', page: number, pageSize: number) => {
  const query = rison.encode({ filter: input, page, page_size: pageSize });
  return SupersetClient.get({
    endpoint: `/api/v1/${RESOURCE}/related/dataset?q=${query}`,
  }).then(response => ({
    data: response.json.result.map((item: { value: number; text: string }) => ({
      label: item.text,
      value: item.value,
    })),
    totalCount: response.json.count,
  }));
};

function ExemptModal({
  show,
  onHide,
  onSave,
  addDangerToast,
  addSuccessToast,
}: ExemptModalProps) {
  const handleFormSubmit = async (values: { dataset: number }) => {
    try {
      await SupersetClient.post({
        endpoint: `/api/v1/${RESOURCE}/`,
        jsonPayload: { dataset: values.dataset },
      });
      addSuccessToast(t('Exempt dataset added.'));
    } catch (err) {
      addDangerToast(
        t('This dataset is already exempt, or could not be saved.'),
      );
      throw err;
    }
  };

  return (
    <FormModal
      show={show}
      onHide={onHide}
      name="add-exempt-dataset"
      title={
        <ModalTitleWithIcon
          title={t('Add exempt dataset')}
          icon={<Icons.PlusOutlined />}
        />
      }
      onSave={onSave}
      formSubmitHandler={handleFormSubmit}
      requiredFields={['dataset']}
      initialValues={{}}
    >
      <FormItem
        name="dataset"
        label={t('Dataset')}
        rules={[{ required: true, message: t('Dataset is required') }]}
      >
        <AsyncSelect
          ariaLabel={t('Dataset')}
          placeholder={t('Select a dataset')}
          options={loadDatasetOptions}
          getPopupContainer={trigger =>
            trigger.closest('.ant-modal-content') as HTMLElement
          }
        />
      </FormItem>
    </FormModal>
  );
}

function GuestRlsExemptDatasetList({ addDangerToast, addSuccessToast }: Props) {
  const {
    state: { loading, resourceCount, resourceCollection },
    fetchData,
    refreshData,
  } = useListViewResource<ExemptObject>(
    RESOURCE,
    t('exempt dataset'),
    addDangerToast,
  );

  const [showModal, setShowModal] = useState(false);

  const handleDelete = useCallback(
    async (row: ExemptObject) => {
      try {
        await SupersetClient.delete({
          endpoint: `/api/v1/${RESOURCE}/${row.id}`,
        });
        refreshData();
        addSuccessToast(t('Removed exempt dataset'));
      } catch (err) {
        addDangerToast(t('There was an issue removing the exempt dataset.'));
      }
    },
    [addDangerToast, addSuccessToast, refreshData],
  );

  const columns = useMemo(
    () => [
      {
        accessor: 'id',
        id: 'id',
        Header: 'ID',
        hidden: true,
      },
      {
        accessor: 'dataset.table_name',
        id: 'dataset',
        Header: t('Dataset'),
        disableSortBy: true,
        Cell: ({ row: { original } }: any) => (
          <span>{original.dataset?.table_name}</span>
        ),
      },
      {
        Cell: ({ row: { original } }: any) => {
          const actions = [
            {
              label: 'delete-action',
              tooltip: t('Remove'),
              placement: 'bottom',
              icon: 'DeleteOutlined',
              onClick: () => handleDelete(original),
            },
          ] as ListViewActionProps[];
          return <ListViewActionsBar actions={actions} />;
        },
        Header: t('Actions'),
        id: 'actions',
        hidden: false,
        disableSortBy: true,
        size: 'sm',
      },
    ],
    [handleDelete],
  );

  const filters: ListViewFilters = useMemo(() => [], []);

  const subMenuButtons: SubMenuProps['buttons'] = [
    {
      name: (
        <>
          <Icons.PlusOutlined iconSize="m" /> {t('Exempt dataset')}
        </>
      ),
      buttonStyle: 'primary',
      onClick: () => setShowModal(true),
    },
  ];

  return (
    <>
      <SubMenu name={t('Guest RLS Exempt Datasets')} buttons={subMenuButtons} />
      <ExemptModal
        show={showModal}
        onHide={() => setShowModal(false)}
        onSave={() => {
          refreshData();
          setShowModal(false);
        }}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
      />
      <ListView<ExemptObject>
        className="guest-rls-exempt-dataset-list-view"
        columns={columns}
        count={resourceCount}
        data={resourceCollection}
        fetchData={fetchData}
        refreshData={refreshData}
        filters={filters}
        initialSort={[{ id: 'id', desc: true }]}
        loading={loading}
        pageSize={25}
        addDangerToast={addDangerToast}
        addSuccessToast={addSuccessToast}
        emptyState={{
          title: t('No exempt datasets yet'),
          description: t(
            'Guests must carry an RLS clause for every dataset they query. ' +
              'Add shared/lookup datasets here so they are queryable without ' +
              'one (everything else returns no rows).',
          ),
          buttonText: (
            <>
              <Icons.PlusOutlined iconSize="m" /> {t('Exempt dataset')}
            </>
          ),
          buttonAction: () => setShowModal(true),
        }}
      />
    </>
  );
}

export default withToasts(GuestRlsExemptDatasetList);
