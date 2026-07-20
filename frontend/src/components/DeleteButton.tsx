import { DeleteOutlined } from "@ant-design/icons";
import { Button, Popconfirm } from "antd";

type DeleteButtonProps = {
  disabled?: boolean;
  loading?: boolean;
  title?: string;
  onConfirm: () => void;
};

export function DeleteButton({
  disabled,
  loading,
  title = "确认删除这条记录？",
  onConfirm
}: DeleteButtonProps) {
  return (
    <Popconfirm
      title={title}
      okText="删除"
      cancelText="取消"
      okButtonProps={{ danger: true }}
      disabled={disabled}
      onConfirm={onConfirm}
    >
      <Button size="small" danger icon={<DeleteOutlined />} loading={loading} disabled={disabled}>
        删除
      </Button>
    </Popconfirm>
  );
}
