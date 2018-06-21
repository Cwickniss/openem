/// @file
/// @brief Implementation for finding rulers in images.

#include "find_ruler.h"

#include <future>
#include <queue>
#include <mutex>

#include <opencv2/imgproc.hpp>
#include <tensorflow/core/public/session.h>
#include <tensorflow/core/platform/env.h>

namespace openem { namespace find_ruler {

namespace tf = tensorflow;

namespace {

/// Does preprocessing on an image.
/// @param image Image to preprocess.
/// @param width Required width of the image.
/// @param height Required height of the image.
/// @return Preprocessed image.
tf::Tensor Preprocess(const cv::Mat& image, int width, int height);

} // namespace

/// Implementation details for RulerMaskFinder.
class RulerMaskFinder::RulerMaskFinderImpl {
 public:
  /// Constructor.
  RulerMaskFinderImpl();

  /// Does processing on the current queue.  This is launched by
  /// Process in a separate thread.
  tf::Tensor RunModel();

  /// Tensorflow session.
  std::unique_ptr<tensorflow::Session> session_;

  /// Input image width.
  uint64_t width_;

  /// Input image height.
  uint64_t height_;

  /// Batch size, computed from available memory.
  uint64_t batch_size_;

  /// Indicates whether the model has been initialized.
  bool initialized_;

  /// Queue of futures containing preprocessed images.
  std::queue<std::future<tensorflow::Tensor>> preprocessed_;

  /// Mutex for handling concurrent access to image queue.
  std::mutex mutex_;

  /// User defined callback, executed when Process completes.
  UserCallback callback_;
};

//
// Implementations
//

namespace {

tf::Tensor Preprocess(
    const cv::Mat& image, 
    int width, 
    int height) {

  // Start by resizing the image if necessary.
  cv::Mat p_image;
  if ((image.rows != height) || (image.cols != width)) {
    cv::resize(image, p_image, cv::Size(width, height));
  }
  else {
    p_image = image.clone();
  }

  // Convert to RGB as required by the model.
  cv::cvtColor(p_image, p_image, CV_BGR2RGB);

  // Do image scaling.
  p_image.convertTo(p_image, CV_32F, 1.0 / 128.0, -1.0);

  // Copy into tensor.
  tf::Tensor tensor(tf::DT_FLOAT, tf::TensorShape({1, height, width, 3}));
  auto flat = tensor.flat<float>();
  std::copy_n(p_image.ptr<float>(), p_image.total(), flat.data());
  return tensor;
}

} // namespace

RulerMaskFinder::RulerMaskFinderImpl::RulerMaskFinderImpl()
    : session_(nullptr),
      width_(0),
      height_(0),
      batch_size_(64),
      initialized_(false),
      mutex_(),
      callback_(nullptr) {
}

tf::Tensor RulerMaskFinder::RulerMaskFinderImpl::RunModel() {
  tf::Tensor tensor;
  return tensor;
}

RulerMaskFinder::RulerMaskFinder() : impl_(new RulerMaskFinderImpl()) {}

RulerMaskFinder::~RulerMaskFinder() {}

ErrorCode RulerMaskFinder::Init(
    const std::string& model_path, 
    UserCallback callback) {
  impl_->initialized_ = false;

  // Read in the graph.
  tf::GraphDef graph_def;
  tf::Status status = tf::ReadBinaryProto(
      tf::Env::Default(), model_path, &graph_def);
  if (!status.ok()) return kErrorLoadingModel;

  // Find the input shape based on graph definition.  For now we avoid
  // using protobuf map functions so we don't have to link with 
  // protobuf.
  bool found = false;
  for (auto p : graph_def.node(0).attr()) {
    if (p.first == "shape") {
      found = true;
      auto shape = p.second.shape();
      if (shape.dim_size() != 4) return kErrorGraphDims;
      impl_->width_ = shape.dim(2).size();
      impl_->height_ = shape.dim(1).size();
    }
  }
  if (!found) return kErrorNoShape;

  // Create a new tensorflow session.
  tf::Session* session;
  status = tf::NewSession(tf::SessionOptions(), &session);
  if (!status.ok()) return kErrorTfSession;
  impl_->session_.reset(session);

  // Create the tensorflow graph.
  status = impl_->session_->Create(graph_def);
  if (!status.ok()) return kErrorTfGraph;
  impl_->initialized_ = true;
  return kSuccess;
}

int RulerMaskFinder::MaxImages() {
  return impl_->batch_size_;
}

ErrorCode RulerMaskFinder::AddImage(const cv::Mat& image) {
  if (!impl_->initialized_) return kErrorBadInit;
  if (!image.isContinuous()) return kErrorNotContinuous;
  auto f = std::async(
      std::launch::async, 
      Preprocess, 
      image, 
      impl_->width_, 
      impl_->height_);
  impl_->mutex_.lock();
  impl_->preprocessed_.push(std::move(f));
  impl_->mutex_.unlock();
  return kSuccess;
}

ErrorCode RulerMaskFinder::Process() {
  if (!impl_->initialized_) return kErrorBadInit;
  // TODO(Jon) Kick off a new thread and process the queue.
  return kSuccess;
}

bool RulerPresent(const cv::Mat& mask) {
  return false;
}

double RulerOrientation(const cv::Mat& mask) {
  double orientation = 0.0;
  return orientation;
}

cv::Mat Rectify(const cv::Mat& image, const double orientation) {
  cv::Mat r_image;
  return r_image;
}

cv::Rect FindRoi(const cv::Mat& mask, int h_margin, int v_margin) {
  cv::Rect roi;
  return roi;
}

cv::Mat Crop(const cv::Mat& image, const cv::Rect& roi) {
  cv::Mat c_image;
  return c_image;
}

}} // namespace openem::find_ruler

